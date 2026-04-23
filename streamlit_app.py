import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from google import genai
from google.genai import types
import time
import json

# --- GOOGLE AI SETUP ---
try:
    # Ensure GEMINI_API_KEY is in your Streamlit Secrets
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("API Key missing or invalid in Secrets. Please check your setup.")
    st.stop()

# --- SESSION STATE ---
if "mastery" not in st.session_state:
    st.session_state.mastery = {}
if "current_view" not in st.session_state:
    st.session_state.current_view = "map"
if "web_data" not in st.session_state:
    st.session_state.web_data = None
if "selected_node" not in st.session_state:
    st.session_state.selected_node = None

# --- AI FUNCTIONS ---
def generate_web_data(topic):
    prompt = f"Act as a curriculum expert. For the topic '{topic}', identify 5 key sub-topics. Return ONLY a JSON object: {{\"sub_topics\": [\"topic1\", \"topic2\", \"topic3\", \"topic4\", \"topic5\"]}}"
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)["sub_topics"]

def generate_questions(node_label):
    prompt = f"Generate 5 MCQs for: {node_label}. Provide 3 options, the correct answer, and an explanation for why it is correct. Return ONLY a JSON list: [{{\"q\": \"...\", \"options\": [\"...\", \"...\"], \"correct\": \"...\", \"explanation\": \"...\"}}]"
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

def stream_text(text):
    for word in text.split():
        yield word + " "
        time.sleep(0.04)

# --- VIEW: KNOWLEDGE MAP ---
def show_map_view():
    st.title("🕸️ Knowledge Map Navigator")
    st.markdown("""
    <style>
        /* This targets the container holding the graph */
        iframe[title="streamlit_agraph.agraph"] {
            display: block;
            margin: 0 auto !important;
            width: 95% !important;
            height: 600px !important;
            border: 2px solid #f0f2f6; 
            border-radius: 15px;
            background-color: #fafafa;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)
   
    with st.sidebar:
        st.header("Syllabus Input")
        topic_input = st.text_input("Enter Topic:", placeholder="e.g. Plate Tectonics")
        if st.button("Generate Web"):
            with st.spinner("Gemini is spinning the web..."):
                branches = generate_web_data(topic_input)
                st.session_state.web_data = {"center": topic_input, "branches": branches}
                st.session_state.mastery = {b: "#d3d3d3" for b in branches}
                st.rerun()

    if st.session_state.web_data:
    
            nodes = [Node(id=st.session_state.web_data["center"],
                      label=st.session_state.web_data["center"],
                      size=55,
                      shape="ellipse",
                      color="#FFD700",
                      font={'size': 20, 'color': 'black', 'face': 'Arial', 'weight': 'bold'})]
       
        edges = []
        for b in st.session_state.web_data["branches"]:
            color = st.session_state.mastery.get(b, "#d3d3d3")
            nodes.append(Node(id=b, label=b, size=40, shape="ellipse", color=color, font={'size': 16, 'color': 'black'}))
            edges.append(Edge(source=st.session_state.web_data["center"], target=b, width=3))

        # Spider Web Physics Config
        config = Config(
            width=1200,
            height=600,
            physics=True,
            fit_canvas=True,
            
            barnesHut={
                "gravitationalConstant": -25000, 
                "centralGravity": 0.1,
                "springLength": 250,
                "springConstant": 0.04,
                "avoidOverlap": 1,
            },
            minVelocity=0.75,
            mxvelocity=50,
            staticGraphWithDragAndDrop=True,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6"
        )
    
        clicked = agraph(nodes=nodes, edges=edges, config=config)

        if clicked and clicked != st.session_state.web_data["center"]:
            st.session_state.selected_node = clicked
            st.session_state.current_view = "quiz"
            st.rerun()
    else:
        st.info("👈 Enter a topic in the sidebar to start building your map.")

# --- VIEW: QUIZ ---
def show_quiz_view():
    node = st.session_state.selected_node
    st.button("⬅ Back to Map", on_click=lambda: setattr(st.session_state, "current_view", "map"))
   
    # Cache questions for this session
    if "active_questions" not in st.session_state or st.session_state.get("last_node") != node:
        with st.spinner(f"Gemini is generating questions for {node}..."):
            st.session_state.active_questions = generate_questions(node)
            st.session_state.last_node = node

    st.title(f"Checkpoint: {node}")
   
    with st.form("quiz_form"):
        user_responses = []
        for i, q in enumerate(st.session_state.active_questions):
            st.write(f"**Question {i+1}:** {q['q']}")
            ans = st.radio("Choose one:", q['options'], key=f"ans_{i}", label_visibility="collapsed")
            user_responses.append(ans)
       
        if st.form_submit_button("Submit Assessment"):
            correct_count = 0
            for i, q in enumerate(st.session_state.active_questions):
                if user_responses[i] == q['correct']:
                    st.success(f"Q{i+1}: Correct!")
                    correct_count += 1
                else:
                    st.error(f"Q{i+1}: Incorrect.")
                    st.write_stream(stream_text(q['explanation']))
           
            # Mastery Logic: All correct = Green, anything else = Red
            st.session_state.mastery[node] = "#28a745" if correct_count == 5 else "#dc3545"
            st.info("Result saved! Use the button above to go back to the map.")

# --- ROUTING ---
if st.session_state.current_view == "map":
    show_map_view()
else:
    show_quiz_view()
