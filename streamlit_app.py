import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from google import genai
from google.genai import types
import time
import json

# --- GOOGLE AI SETUP ---
# We retrieve the key from Streamlit Secrets for security
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("API Key not found. Please add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
if "mastery" not in st.session_state:
    st.session_state.mastery = {}
if "current_view" not in st.session_state:
    st.session_state.current_view = "map"
if "web_data" not in st.session_state:
    st.session_state.web_data = None

# --- AI FUNCTIONS ---
def generate_web_data(topic):
    prompt = f"Act as a curriculum expert. For the topic '{topic}', identify 5 key sub-topics. Return ONLY a JSON object: {{\"sub_topics\": [\"topic1\", \"topic2\", ...]}}"
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)["sub_topics"]

def generate_questions(node_label):
    prompt = f"Generate 5 MCQs for: {node_label}. Return ONLY a JSON list: [{{\"q\": \"...\", \"options\": [\"A\", \"B\", \"C\"], \"correct\": \"A\", \"explanation\": \"...\"}}]"
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

# --- UI LOGIC ---
if st.session_state.current_view == "map":
    st.title("🕸️ Knowledge Map Explorer")
   
    with st.sidebar:
        st.header("Teacher Input")
        topic_input = st.text_input("Core Topic:", placeholder="e.g. Ecosystems")
        if st.button("Generate Map"):
            with st.spinner("Gemini is building your map..."):
                branches = generate_web_data(topic_input)
                st.session_state.web_data = {"center": topic_input, "branches": branches}
                st.session_state.mastery = {b: "#d3d3d3" for b in branches}

    if st.session_state.web_data:
        nodes = [Node(id=st.session_state.web_data["center"], label=st.session_state.web_data["center"], size=600, color="#FFD700")]
        edges = []
        for b in st.session_state.web_data["branches"]:
            nodes.append(Node(id=b, label=b, color=st.session_state.mastery.get(b, "#d3d3d3"), size=400))
            edges.append(Edge(source=st.session_state.web_data["center"], target=b))

        config = Config(width=1000, height=600, physics=True)
        clicked = agraph(nodes=nodes, edges=edges, config=config)

        if clicked and clicked != st.session_state.web_data["center"]:
            st.session_state.selected_node = clicked
            st.session_state.current_view = "quiz"
            st.rerun()

else:
    node = st.session_state.selected_node
    st.button("⬅ Back to Map", on_click=lambda: setattr(st.session_state, "current_view", "map"))
   
    if "active_questions" not in st.session_state or st.session_state.get("last_node") != node:
        with st.spinner(f"Preparing questions for {node}..."):
            st.session_state.active_questions = generate_questions(node)
            st.session_state.last_node = node

    st.title(f"Mastery Check: {node}")
    with st.form("quiz_form"):
        user_ans = [st.radio(q['q'], q['options'], key=f"q_{i}") for i, q in enumerate(st.session_state.active_questions)]
        if st.form_submit_button("Submit"):
            correct_count = 0
            for i, q in enumerate(st.session_state.active_questions):
                if user_ans[i] == q['correct']:
                    st.success(f"Q{i+1}: Correct!")
                    correct_count += 1
                else:
                    st.error(f"Q{i+1}: Incorrect. Correct: {q['correct']}")
                    st.write_stream(stream_text(q['explanation']))
           
            st.session_state.mastery[node] = "#28a745" if correct_count == 5 else "#dc3545"
            st.info("Map updated. Go back to see your progress!")
