import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import time
import json
from google import genai
from google.genai import types

# 1. PAGE CONFIG
st.set_page_config(
    page_title="Revision Map",
    page_icon="📚",
    layout="wide"
)

# --- GOOGLE AI SETUP ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("API Key missing or invalid in Streamlit Secrets.")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
if "mastery" not in st.session_state:
    st.session_state.mastery = {}
if "current_view" not in st.session_state:
    st.session_state.current_view = "map"
if "web_data" not in st.session_state:
    st.session_state.web_data = None
if "selected_node" not in st.session_state:
    st.session_state.selected_node = None

# --- AI FUNCTIONS ---

def generate_knowledge_web(topic, level):
    """Triggers Gemini to build a curriculum-aligned sub-topic list."""
    if not topic or not level:
        return

    with st.spinner(f"Building your {level} map for {topic}..."):
        try:
            # THE PROMPT
            prompt = f"""
            Act as an expert Edexcel Physics teacher.
            The student is studying {level}.
            Create a detailed knowledge map for the unit: '{topic}'.
            Identify exactly 8 essential sub-topics that appear in the Edexcel specification.
            Return ONLY a JSON object: {{"sub_topics": ["topic1", "topic2", "topic3", "topic4", "topic5", "topic6", "topic7", "topic8"]}}
            """
           
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
           
            branches = json.loads(response.text)["sub_topics"]
            st.session_state.web_data = {
                "center": topic,
                "branches": branches
            }
            st.rerun()
        except Exception as e:
            st.error(f"AI Generation failed: {e}")

def generate_questions(node_label, level):
    """Generates MCQs strictly aligned with Edexcel GCSE Higher Tier standards."""
    try:
        prompt = f""" 
        Act as a Senior Edexcel GCSE Physics Examiner. 
        Your task is to generate 5 Higher Tier MCQs for the sub-topic: '{node_label}'. 
        
        STRICT SYLLABUS BOUNDARIES:
        - ONLY include content found in the Edexcel GCSE (9-1) Physics specification.
        - DO NOT include A-Level concepts (e.g., avoid SUVAT, thermal physics beyond particle model, or complex circular motion).
        - Use ONLY Edexcel command words: 'State', 'Describe', 'Explain', 'Calculate', 'Determine', 'Estimate'. 
        
        QUESTION QUALITY RULES: 1. Difficulty: Target Grade 7-9 (Higher Tier) but keep it within GCSE math limits.
       
        2. Format: 1 clear question, 3 plausible distractors based on common student misconceptions, 1 correct answer.
        3. Logic: For 'Explain' questions, the explanation must link a statement with a reason (using 'because' or 'therefore'). 
        4. Math: Calculations should be 1-2 steps maximum. 
        
        Return ONLY a JSON list: [{{"q": "...", "options": ["...", "...", "..."], "correct": "...", "explanation": "..."}}] """
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)
except Exception as e:
    st.error(f"Quiz Generation Failed: {e}")
    return []

def stream_text(text):
    for word in text.split():
        yield word + " "
        time.sleep(0.04)

# --- SIDEBAR UI ---
with st.sidebar:
    st.image("IMG_0202.png", use_container_width=True)
    st.title("Level and Topic Selection")
   
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
            # Store level in session state for the quiz prompt later
            st.session_state.user_level = selected_level
    else:
        st.info("Choose a level to begin.")
   
    st.divider()

# --- VIEW: KNOWLEDGE MAP ---
def show_map_view():
    st.title("🎯 Revision Map 💭")
    st.markdown("<style>iframe {display: block; margin: 0 auto !important;}</style>", unsafe_allow_html=True)

    if st.session_state.web_data:
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

        config = Config(
            width=1200, height=800, physics=True, fit_canvas=True,
            initialZoom=1.0, staticGraph=False, solver="repulsion",
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
        st.info("👈 Select a topic in the sidebar to build your knowledge map.")

# --- VIEW: QUIZ ---
def show_quiz_view():
    node = st.session_state.selected_node
    level = st.session_state.get("user_level", "GCSE")
   
    if st.button("⬅ Back to Map"):
        st.session_state.current_view = "map"
        st.rerun()

    if "active_questions" not in st.session_state or st.session_state.get("last_node") != node:
        with st.spinner(f"Generating examiner-style questions for {node}..."):
            st.session_state.active_questions = generate_questions(node, level)
            st.session_state.last_node = node

    st.title(f"Checkpoint: {node}")

    with st.form("quiz_form"):
        user_responses = []
        for i, q in enumerate(st.session_state.active_questions):
            st.write(f"**Question {i+1}:** {q['q']}")
            ans = st.radio("Choose one:", q['options'], index=None, key=f"ans_{i}")
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

            st.session_state.mastery[node] = "#28a745" if correct_count == 5 else "#dc3545"

# --- ROUTING ---
if st.session_state.current_view == "map":
    show_map_view()
else:
    show_quiz_view()
