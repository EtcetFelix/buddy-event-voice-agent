import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    inference,
    metrics,
    ChatContext,
    ChatMessage,
)
from livekit.plugins import silero
from livekit.plugins import openai
from livekit.plugins import elevenlabs
from livekit.plugins import assemblyai
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from buddy.tools import find_nearby_events
from buddy.prompts import buddy_instructions_prompt

from buddy.rag import get_rag

logger = logging.getLogger("agent")

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        # Initialize RAG
        self.rag = get_rag(top_k=3)
        
        # Buddy's personality and instructions
        super().__init__(
            instructions=buddy_instructions_prompt,
            tools=[find_nearby_events]
        )
    
    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        """
        Called after user finishes speaking, before agent generates reply.
        This is where we inject RAG context for the LLM.
        """
        # Get the user's message text
        user_text = new_message.text_content
        
        if not user_text:
            return
        
        # Retrieve relevant context from RAG
        rag_context = self.rag.retrieve(user_text)
        
        if rag_context:
            # Add context as a system message that won't be persisted
            turn_ctx.add_message(
                role="assistant",
                content=f"""Relevant information from your memory:

{rag_context}

Use this information naturally in your response when relevant, but don't explicitly mention that you're referencing your memory."""
            )
            logger.info(f"Added RAG context for user message: {user_text[:50]}...")

def prewarm(proc: JobProcess):
    """Prewarm models and initialize RAG during worker startup."""
    proc.userdata["vad"] = silero.VAD.load()
    # Prewarm RAG as well
    try:
        get_rag(top_k=3)
        logger.info("✅ RAG prewarmed")
    except Exception as e:
        logger.error(f"❌ Failed to prewarm RAG: {e}")


async def entrypoint(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up voice AI pipeline
    session = AgentSession(
        stt=assemblyai.STT(),
        llm=openai.LLM(model="gpt-4.1-nano-2025-04-14"),
        tts=elevenlabs.TTS(
            voice_id="ODq5zmih8GrVes37Dizd",
            model="eleven_multilingual_v2"
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
    )

    # Metrics collection
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
    )

    # Join the room
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm, initialize_process_timeout=60))