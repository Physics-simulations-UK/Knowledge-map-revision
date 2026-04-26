import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import time
import json
from google import genai
from google.genai import types

# 1. PAGE CONFIG (Must be the very first Streamlit command)
st.set_page_config(
    page_title="Revision Knowledge Map",
    page_icon="",
    layout="wide"
)

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

# --- AI FUNCTIONS (Defined early to avoid NameErrors) ---

def generate_knowledge_web(topic, level):
    """Triggers the Gemini model to build the sub-topic list."""
    with st.spinner(f"Gemini is building your {level} map..."):
        prompt = f"Act as a curriculum expert for {level}. For the topic '{topic}', identify 8 key sub-topics. Return ONLY a JSON object: {{\"sub_topics\": [\"topic1\", \"topic2\", \"topic3\", \"topic4\", \"topic5\", \"topic6\", \"topic7\", \"topic8\"]}}"
       
        response = client.models.generate_content(
            model="gemini-1.5-flash", # Note: Mapping to stable flash name for reliability
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
       
        try:
            branches = json.loads(response.text)["sub_topics"]
            st.session_state.web_data = {
                "center": topic,
                "branches": branches
            }
            st.rerun()
        except Exception as e:
            st.error(f"Error parsing AI response: {e}")

def generate_questions(node_label):
    prompt = f"Generate 5 MCQs for: {node_label}. Provide 3 options, the correct answer, and an explanation for why it is correct. Return ONLY a JSON list: [{{\"q\": \"...\", \"options\": [\"...\", \"...\"], \"correct\": \"...\", \"explanation\": \"...\"}}]"
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

def stream_text(text):
    for word in text.split():
        yield word + " "
        time.sleep(0.04)

# --- SIDEBAR UI ---
with st.sidebar:
    st.image("IMG_0202.png", use_container_width=True)
    st.title("Syllabus and Topic Selection")
   
    curriculum = {
        "GCSE (Edexcel)": [
            "Topic 1: Key Concepts of Physics", "Topic 2: Motion and Forces",
            "Topic 3: Conservation of Energy", "Topic 4: Waves",
            "Topic 5: Light and the Electromagnetic Spectrum", "Topic 6: Radioactivity",
            "Topic 7: Astronomy", "Topic 8: Energy - Forces doing Work",
            "Topic 9: Forces and their Effects", "Topic 10: Electricity and Circuits",
            "Topic 11: Static Electricity", "Topic 12: Magnetism and the Motor Effect",
            "Topic 13: Electromagnetic Induction", "Topic 14: Particle Model",
            "Topic 15: Forces and Matter"
        ],
        "IAL (Pearson Edexcel)": [
            "Unit 1: Mechanics and Materials", "Unit 2: Waves and Electricity",
            "Unit 3: Practical Skills I", "Unit 4: Further Mechanics, Fields and Particles",
            "Unit 5: Thermodynamics, Radiation, Oscillations and Cosmology",
            "Unit 6: Practical Skills II"
        ]
    }

    selected_level = st.selectbox("Select Level:", options=list(curriculum.keys()), index=None)

    if selected_level:
        selected_unit = st.selectbox(f"Select {selected_level} Unit:", options=curriculum[selected_level], index=None)

        if selected_unit and st.button("Generate Web"):
            generate_knowledge_web(selected_unit, selected_level)
    else:
        st.info("Choose a level to begin.")
   
    st.divider()

# --- VIEW: KNOWLEDGE MAP ---
def show_map_view():
    st.title("🕸️ Knowledge Map Navigator")
    # CSS to center the map iframe
    st.markdown("<style>iframe {display: block; margin: 0 auto !important;}</style>", unsafe_allow_html=True)

    if st.session_state.web_data:
        # Define Nodes
        nodes = [Node(id=st.session_state.web_data["center"],
                      label=st.session_state.web_data["center"],
                      size=50, shape="ellipse", color="#FFD700",
                      font={'size': 20, 'weight': 'bold'},
                      **{'x': 0, 'y': 0, 'fixed': True})]

        edges = []
        for b in st.session_state.web_data["branches"]:
            color = st.session_state.mastery.get(b, "#d3d3d3")
            nodes.append(Node(id=b, label=b, size=40, shape="ellipse", color=color, font={'size': 14}))
            edges.append(Edge(source=st.session_state.web_data["center"], target=b, width=3))

        # Your specific Physics/Agraph Config
        config = Config(
            width=1200,
            height=800,
            physics=True,
            fit_canvas=True,
            initialZoom=1.0,
            staticGraph=False,
            solver="repulsion",
            repulsion={
                "nodeDistance": 400,
                "centralGravity": 0.1,
                "springLength": 300,
                "springConstant": 0.05,
            },
            interaction={"dragNodes": True, "dragView": False, "zoomView": False},
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
        st.info("👈 Choose a level and topic in the sidebar to start.")

# --- VIEW: QUIZ ---
def show_quiz_view():
    node = st.session_state.selected_node
   
    if st.button("⬅ Back to Map"):
        st.session_state.current_view = "map"
        st.rerun()

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
            ans = st.radio("Choose one:", q['options'], index=None, key=f"ans_{i}", label_visibility="collapsed")
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

# --- MAIN ROUTING ---
if st.session_state.current_view == "map":
    show_map_view()
else:
    show_quiz_view()
