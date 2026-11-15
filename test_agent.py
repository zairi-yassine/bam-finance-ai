from agent.graph import agent

question = "What was the Consumer price index in 2021 according to the English report?"
print(f"User: {question}\n")

result = agent.invoke({"question": question})
print(f"AI Answer: {result['answer']}\n")
print(f"Generated SQL: {result['sql_query']}")