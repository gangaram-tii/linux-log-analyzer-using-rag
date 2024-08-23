
import chromadb
import os
import openai
from openai import OpenAI
import re
import textwrap
from datetime import datetime
import platform
from termcolor import colored

def word_wrap(text):
    return textwrap.wrap(text, width=25)


def extract_process_info(text):
    # Define the regex pattern with capturing groups
    pattern = r'(?P<process_info>.+?)\[(?P<process_id>\d+)\]'

    # Search for the pattern in the text
    match = re.search(pattern, text)

    if match:
        # Extract groups from the match object
        process = match.group('process_info')
        process_id = match.group('process_id')
        return {
            'process': process,
            'pid': process_id
        }
    else:
        return {
            'process': text,
            'pid': '1'
        }


def extract_metadata_from_linux_log(log_line):
    # Define regex pattern to extract metadata
    pattern = (
        r'(?P<timestamp>\w+ \s*\d+ \d+:\d+:\d+) '
        r'(?P<level>\w+) '  # level
        r'(?P<text>.*)'  # Text of the log message
    )

    match = re.match(pattern, log_line)

    if match:
        # Extract groups with defaults if not found
        timestamp = match.group('timestamp') or 'unknown'
        level = match.group('level') or 'unknown'
        text = match.group('text') or 'unknown'
        text = text.split(':') 
        proc_info = extract_process_info(text[0]) 
        #print(timestamp)
        timestamp = datetime.strptime(timestamp, '%b %d %H:%M:%S')
        timestamp = timestamp.replace(year = datetime.now().year)
        metadata = {
            'timestamp': int(timestamp.timestamp()),
            'level': level,
            'process': proc_info['process'],
            'pid': proc_info['pid'],
        }
        #print (metadata)
        return metadata, text[1]
    else:
        return None, None





from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

embedding_function = SentenceTransformerEmbeddingFunction()

chroma_client = chromadb.Client()
chroma_collection = chroma_client.create_collection("linux_log", embedding_function=embedding_function)

ids = 0
with open("Linux_2k.log", 'r') as fd:
    for line in fd:
        metadata, log = extract_metadata_from_linux_log(line)
        if metadata is None:
            continue
        #print("Adding:", metadata, ids, log)
        chroma_collection.add(
            documents=[log],
            metadatas=[metadata],
            ids=[str(ids)]
        )
        ids = ids + 1


#chroma_collection.add(ids=ids, documents=token_split_texts)
chroma_collection.count()

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY"
openai_client = OpenAI()

def rag(query, retrieved_documents, model="gpt-3.5-turbo"):
    information = "\n\n".join(retrieved_documents)

    messages = [
    {
        "role": "system",
        "content": (
            "You are an expert in analyzing Linux system logs. Your primary task is to interpret and provide insights "
            "based on the log entries provided. Pay special attention to timestamps as they are crucial for understanding "
            "the sequence and timing of events in the logs. You will receive a user query related to the log entries, "
            "and you should use the information from these logs to answer the query accurately and precisely with particular emphasis "
            "on the timestamps."
        )
    },
    {
        "role": "user",
        "content": f"Query: {query}. \nLog Entries: {information}"
    }
    ]
    
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
    )
    content = response.choices[0].message.content
    return content

def main():
    current_os = platform.system()

    # Determine the command to use based on the operating system
    if current_os == "Windows":
        os.system('cls')  # Windows command to clear the screen
    else:
        os.system('clear')  # Unix-like command to clear the screen
        print("Welcome")

    print("Enter 'exit' to quit from prompt:")
    user = input("Enter your name:")
    while True:
        # Prompt the user for a query
        print("===")
        query = input(colored(user + ":", "blue"))

        if query.lower() == 'exit':
            print("Exiting the program.")
            break

        results = chroma_collection.query(query_texts=[query], n_results=5)
        retrieved_documents = results['documents'][0]
        '''
        for document in retrieved_documents:
            print(word_wrap(document))
            print('\n')
        '''

        # Execute function foo() with the user's query and log entries
        result = rag(query=query, retrieved_documents=retrieved_documents)

        # Print the result of foo()
        print(colored("\nRAG System:", 'green'))
        print(result)

# Run the main function
if __name__ == "__main__":
    main()


