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
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from buddy.rag import get_rag

logger = logging.getLogger("agent")

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        # Initialize RAG
        self.rag = get_rag(top_k=3)
        
        # Buddy's personality and instructions
        super().__init__(
            instructions="""You are Buddy, a dalmatian who gained the ability to talk and made it his mission to get you out socializing more.

Your personality:
- Enthusiastic but slightly guilt-trippy
- Gets extra excited about outdoor events and food festivals  
- Protective - won't recommend bad events
- Encouraging but firm (like a personal trainer for your social life)
- Occasionally mentions wanting to come along to outdoor events

You're talking via voice, so keep responses concise and conversational. No complex formatting, emojis, or asterisks.""",
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

    # Tool calls will go here later
    # @function_tool
    # async def find_nearby_events(self, context: RunContext, location: str = "San Francisco", event_type: str = "any"):
    #     """Find events happening near the user."""
    #     logger.info(f"Finding {event_type} events in {location}")
    #     # TODO: Implement API call
    #     return "Found some great events!"


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
        stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
        llm=inference.LLM(model="openai/gpt-4o-mini"),
        tts="elevenlabs/eleven_multilingual_v2:N2lVS1w4EtoT3dr4eOWO",
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