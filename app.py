import streamlit as st
from git import Repo
import os
import shutil
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers import LanguageParser
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationSummaryMemory
# import config

# Define the path where you want to clone the repository
repo_path = "loaded-repo"
os.environ['GIT_LFS_SKIP_SMUDGE'] = '1'

#OPEN_AI_KEY = config.OPEN_AI_KEY
#OPEN_AI_KEY = os.environ.get('OPENAI_API_KEY')

import os

OPEN_AI_KEY = os.environ.get('OPENAI_API_KEY')


# Initialize a placeholder for qa in the session state if not already present
if 'qa' not in st.session_state:
    st.session_state['qa'] = None

def clone_and_process_repository(repo_url):
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    try:
        Repo.clone_from(repo_url, to_path=repo_path)
        st.success("Repository cloned successfully.")
    except Exception as e:
        st.error(f"Failed to clone repository: {e}")
        return []

    loader = GenericLoader.from_filesystem(
        repo_path,
        glob="**/*.py",
        suffixes=[".py"],
        parser=LanguageParser(language=Language.PYTHON, parser_threshold=500)
    )
    documents = loader.load()
    python_splitter = RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON, chunk_size=2000, chunk_overlap=200)
    texts = python_splitter.split_documents(documents)
    return texts

def initialize_conversational_ai(texts):
    embeddings = OpenAIEmbeddings(openai_api_key=OPEN_AI_KEY)
    db = Chroma.from_documents(texts, embeddings)
    retriever = db.as_retriever(search_type="mmr", search_kwargs={"k": 8})
    llm = ChatOpenAI(model_name="gpt-4-turbo-preview", openai_api_key=OPEN_AI_KEY)
    memory = ConversationSummaryMemory(llm=llm, memory_key="chat_history", return_messages=True)
    return ConversationalRetrievalChain.from_llm(llm, retriever=retriever, memory=memory)

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        st.write('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            st.write('{}{}'.format(subindent, f))

st.title("GitHub Repository Chat Interface")
repo_url = st.text_input("Enter GitHub Repository URL:", value="https://github.com/DataWithAlex/gen3-pokeGAN")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if st.button("Process Repository") and repo_url:
    texts = clone_and_process_repository(repo_url)
    if texts:
        # Directly store the initialized qa object in session state
        st.session_state['qa'] = initialize_conversational_ai(texts)
        st.success("Repository cloned successfully and ready to chat. Enter your questions below.")
        st.write("Directory structure of the cloned repository:")
        list_files(repo_path)
    else:
        st.error("Processing the repository failed or it contains no processable content.")

user_input = st.text_input("You:", key="new_input", value="What is this repo about? and how can I hyper parameter tune with it? give me specific code")

if user_input and st.session_state['qa']:
    try:
        result = st.session_state['qa'](user_input)
        response = result['answer']
        st.session_state.chat_history.append(("user", user_input))
        st.session_state.chat_history.append(("assistant", response))
    except Exception as e:
        st.error(f"Error generating response: {e}")

for role, message in st.session_state.chat_history:
    if role == "user":
        # Assuming you want to display messages from the user differently
        with st.container():
            st.write(f"User: {message}")
    else:
        # And here, handling messages from the assistant/AI
        with st.container():
            st.write(f"AI: {message}")
