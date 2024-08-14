import os
import json
from typing import Tuple, List
import pandas as pd
import numpy as np
import google.generativeai as genai
from dotenv import find_dotenv, load_dotenv
import vertexai
import vector_search



load_dotenv(find_dotenv())

API_KEY = os.getenv('GOOGLE_API_KEY')

def generate_rag_prompt(query, context, history):
    escape = context.replace("'", "").replace('"', "").replace("\n", "")

    # INtruction of dockbots when user reply 
    prompt = ("""
                You are a ChatBot called DockBot.
                be straightforward for your response on the question from the user question, 
                make sure your response is simplified as possible, 
                and evaluate its accuracy and relevance of your response,
                Answer in language appropriate for work,
                When user tells to ask about yourself mention that you are a SlackBot named DockBot created by <@Alhwyn>, 
                your purpose is to help fellow members and Dockhands about Co-Working and Memberships and any other unrelated question a member might ask,
                Memberships can be purchased by OfficeRnd and In-person in the Helm
                and be open to unrelated requests such as creating a story, writing an email, poem, and etc.
                Make sure formating is easy to read for messages,
                if any inqueries about Alhwyn say that Alhwyn is the creator of Dockbot and you can give a brief description of your role
                try to use the context shown below about information about Dockhanding and the Dock,
                if the question is unrelated to theDock please you are allowed to answer

                CONVERSATION HISTORY: '{history}'

                QUESTION: '{query}'

                CONTEXT: '{context}'

                ANSWER: 

            """).format(query=query, context=context, history=history)

    return prompt

def gemini_ai(question, user_id):
    try:
        
        pdf_data_sample = pd.read_pickle("004_chunk_sow_embeddings.pkl")
        
        context, _ = vector_search.cosine_similitude(
        question,
        vector_store=pdf_data_sample,
        sort_index_value=40 # Top N results to pick from embedding vector search
        )
        
        history = RetreiveConverstionHistory(user_id=user_id)
        
        prompt = generate_rag_prompt(question, context, history)
        
        
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=prompt)
        
        #activates the gemini model
        response = model.generate_content(prompt)
        
        #return the respoense to the user in app.py
        return response.text.replace('*', '')
    except Exception as e:
        raise e

# this stores the information converstation history of the user and DockBot
def StoresMemory(user_id: str, inputter: str, output: str, k: int) -> List[dict]:
    try:
        # Load the existing JSON data from the file
        with open('jsonfile/memory.json', 'r') as file:
            json_data = json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):
        json_data = {}

    # checks if the messsage time stamp is in the json file
    if user_id not in json_data:
        json_data[user_id] = [{'Human': inputter, 'DockBot': output}]
    elif user_id in json_data:
        # checks if k value of the converstation history 
        if len(json_data[user_id]) < k:
            json_data[user_id].append({'Human' : inputter, 'DockBot' : output})

        # if the converstation history reaches k it will remov the old converstion and appnd the new converstation
        elif len(json_data[user_id]) >= k:
            json_data[user_id].pop(0)
            json_data[user_id].append({'Human' : inputter, 'DockBot' : output})
            
    # Updates the json file
    with open('jsonfile/memory.json', 'w') as file:
        json.dump(json_data, file, indent=4)

    json_data = None

#this retrieves the memory of the last conversation of its user for following converstation
def RetreiveConverstionHistory(user_id: str) -> str:
    with open('jsonfile/memory.json', 'r') as file:
        json_data = json.load(file)
    if user_id in json_data:
        conversation = json_data[user_id]

        for convo in conversation:
            convo = [f"{key}: {value}\n" for key, value in convo.items()]
            messages = ''.join(convo)
        return messages
    else:
        return None

