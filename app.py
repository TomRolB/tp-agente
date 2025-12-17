import chainlit as cl
from interface.chainlit_handler import ChainlitHandler
from final.agents import validate_api_keys

validate_api_keys()
print("✓ Environment validation passed")

@cl.on_chat_start
async def start():
    await ChainlitHandler.init_session()

@cl.on_message
async def main(message: cl.Message):
    await ChainlitHandler.process_message(message)

@cl.action_callback("answer")
@cl.action_callback("new_question")
@cl.action_callback("performance")
async def on_action(action: cl.Action):
    await ChainlitHandler.process_action(action)

