from models.local_llm import LocalLLM

llm = LocalLLM()

answer = llm.generate(

    "You are a helpful assistant.",

    "Say hello in one sentence."

)

print(answer)