"""
This file turns a follow-up question into a full question that stands alone.
For example, "what about its accuracy" becomes a question that names the
thing "its" points to.
This lets the search work on follow-up questions.
"""

import re

from src.generation.llm_client import get_llm
from src.generation.prompt_templates import MAX_HISTORY_TURNS
from src.metrics.tracker import timed, record_llm

# list single words that point back to an earlier turn, grouped by type
# leave out very common words like "that", "which" and "the", because they appear in standalone questions too
POINTER_WORDS = [
    # pronouns that stand for something said before
    "it", "its", "itself", "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "they", "them", "their", "theirs", "themselves",
    # words that point at something nearby
    "this", "these", "those", "such", "there", "here",
    # words that pick one item out of an earlier list
    "former", "latter", "another", "other", "others", "both", "either", "neither", "each", "remaining", "rest",
    # words that point to the position in the chat
    "above", "below", "previous", "previously", "preceding", "following", "earlier", "aforementioned",
    "mentioned", "same", "similar", "next", "last", "before", "prior",
    # words that continue the last topic
    "again", "also", "else", "more", "further", "additionally", "instead", "besides", "furthermore", "too",
]

# match any of the words above
REFERENCE_WORDS = re.compile(r"\b(" + "|".join(POINTER_WORDS) + r")\b", re.IGNORECASE)

# match short phrases that point back, which are safer than the single words "that", "one" or "the"
POINTER_PHRASES = re.compile(
    r"\b("
    # "that" used as a pointer, like "about that" or "that one"
    r"(of|in|on|about|from|for|with|to|by|at|is|was|does|did) that"
    r"|that (one|part|section|point|method|approach|result|answer|chunk|paper|document|file)"
    # "one" or "ones" used as a pointer, like "which one" or "the first one"
    r"|(which|the|this|that|other|another|first|second|third|fourth|last|same|former|latter) ones?"
    # ordinal or position words before a noun, like "the second method"
    r"|the (first|second|third|fourth|fifth|last|latter|former|next|previous|other|same|above|following|earlier|remaining|rest)"
    # references to what was said, like "you said" or "your answer"
    r"|you (said|mentioned|wrote|told|listed|gave)"
    r"|your (answer|reply|response|last|previous|earlier)"
    r"|(the|that|this|last|previous|earlier) (answer|reply|response|question)"
    r"|as (said|mentioned|discussed|shown|stated) (before|above|earlier)"
    r"|so far|just now|a moment ago"
    # asking for more or a reason, like "what else" or "how so"
    r"|what else|anything else|any other|how so|why not|why is that|how come|go on|tell me more|more detail|in more detail|elaborate|expand on"
    r")\b",
    re.IGNORECASE,
)

# match openers that continue the last turn, like "and what about ..."
FOLLOW_UP_OPENERS = re.compile(
    r"^\s*(and|but|also|so|then|what about|how about|ok|okay|thanks|thank you|alright|right|why|really|meaning|i mean)\b",
    re.IGNORECASE,
)

# treat very short questions as follow-ups, because they rarely make sense alone
SHORT_QUESTION_WORDS = 4

def looks_like_follow_up(question: str) -> bool:
    # say yes when the question is very short, starts like a follow-up, or points back with a word like "it"
    if len(question.split()) <= SHORT_QUESTION_WORDS:
        return True
    return bool(
        FOLLOW_UP_OPENERS.search(question)
        or REFERENCE_WORDS.search(question)
        or POINTER_PHRASES.search(question)
    )

# rewrite the question using the chat history
def rewrite_query(question: str, chat_history: list[dict]) -> str:
    # skip rewriting when there is no earlier chat, because the question already stands alone
    if not chat_history:
        return question

    # skip the llm call when the question does not look like a follow-up, which saves time and tokens
    if not looks_like_follow_up(question):
        return question

    llm = get_llm("rewrite")

    # use only the question and answer text, and ignore grounding and citation info
    history_text = "\n".join(
        f"User: {turn['question']}\nAssistant: {turn['answer']}" for turn in chat_history[-MAX_HISTORY_TURNS:]
    )

    prompt = f"""
    Given the conversation history and a follow-up question, rewrite the follow-up question
    into a standalone question that makes sense without the history. \n

    If the follow-up question is already standalone, return it unchanged.
    Only output the rewritten question, nothing else. \n

    Conversation history: {history_text} \n

    Follow-up question: {question} \n

    Standalone question:
    """

    # ask the llm to rewrite, and time the call
    with timed("rewrite"):
        response = llm.invoke(prompt)

    # count the tokens, then remove extra spaces around the reply
    record_llm(response)
    return response.content.strip()
