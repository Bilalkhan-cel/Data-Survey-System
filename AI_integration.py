import os
from openai import AsyncOpenAI
from agents import Agent ,  Runner , OpenAIChatCompletionsModel ,set_tracing_disabled
import asyncio
from dotenv import load_dotenv


load_dotenv()

api=os.getenv("OPEN_ROUTER")

set_tracing_disabled(True)

client=AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api
)

model=OpenAIChatCompletionsModel(
    model="inclusionai/ling-3.0-flash:free",
    openai_client=client
)

agent=Agent(
    name="Survey_Agent",
    instructions="You are a English Master and I will give you the likert Scale ( Survey ) Questions your job is to add a negation in that sentences and make sure that new structure do not mess the likert scale , Respond just the Negated sentence ",
    model=model
)

def change_sentence(sentence):

    try:

        async def main():
            response = await Runner.run(agent, sentence)
            return response.final_output

        return asyncio.run(main())
    except Exception as e:
        return None


