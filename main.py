from ollama import chat


response = chat(
    model ="llama3.2:3b",
    messages=[
        {"role":"system","content":"Eres un asistente útil. Responde siempre en español"},
        {"role":"user","content":"Explica que es un api REST, imagina que eres el servidor y el api rest es tu parea sentimental y debes de t6erminar su relacion de 4 años , termina al api rest de una manera tecnica"}
    ]
)

print (response.message.content)