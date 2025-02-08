from llama_cpp import Llama
import json
from typing import List
from dotenv import load_dotenv
from models import *
import os
import logging
import sys
import contextlib
import signal
from functools import partial
import threading
from ollama import chat
from ollama import ChatResponse
from guardian import *
from url_extractions import extract_urls_from_text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from API_check.email_check import EmailCheck
from API_check.url_check import UrlCheck
from API_check.phone_check import PhoneCheck

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("parent_app.log"), logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    pass


@contextlib.contextmanager
def timeout(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out")

    # Register the signal handler
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)


@contextlib.contextmanager
def redirect_metal_output():
    metal_log = open("metal_init.log", "a")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = metal_log
        sys.stderr = metal_log
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        metal_log.close()


def load_scammer_email():
    try:
        with open("./../config.json", "r") as f:
            config = json.load(f)
            if config.get("scammer_email"):
                return config.get("scammer_email")
            else:
                return None
    except Exception as e:
        logging.error(f"Error loading scammer info: {e}")
        return None


def load_scammer_phone():
    try:
        with open("./../config.json", "r") as f:
            config = json.load(f)
            if config.get("scammer_phone"):
                return config.get("scammer_phone")
            else:
                return None
    except Exception as e:
        logging.error(f"Error loading scammer info: {e}")
        return None


def analyze_sentiment(chats: List[Chat]) -> SentimentResponse:
    logger.info("Starting sentiment analysis")

    try:
        load_dotenv()

        model_path = os.getenv("LLAMA_MODEL_PATH")
        if not model_path:
            logger.error("LLAMA_MODEL_PATH not found in environment variables")
            raise ValueError("LLAMA_MODEL_PATH environment variable is not set")

        # Initialize with reduced context size and optimal parameters
        # with redirect_metal_output():
        #     logger.debug("Creating Llama instance...")
        #     llm = Llama(
        #         model_path=model_path,
        #         n_ctx=512,  # Reduced context size
        #         n_threads=2,  # Reduced threads
        #         n_batch=512,  # Batch size
        #         verbose=False,
        #         # instruct=True  # <-- Uncomment if your model requires "instruct" mode
        #     )

        # logger.info("Model initialized successfully")

        # Prepare chat text with length limit
        # messages_text = "\n".join([f"Sender: {chat.message}" for chat in chats[:5]])
        messages_text = chats[0].message
        if load_scammer_phone():
            phone = load_scammer_phone()
        if load_scammer_email():
            email = load_scammer_email()
            
        url = extract_urls_from_text(messages_text)
        if url:
            url_checker = UrlCheck()
            url_valid = url_checker.check_url(url)["is_safe"]
            if url_valid:
                url_prompt = ",a safe url from the text message after being checked with google safe browser"
            else:
                url_prompt = ",an unsafe url from the text message after being checked with google safe browser"
        else:
            url_prompt = ""
        if not phone:
            phone_checker = PhoneCheck()
            phone_score = phone_checker.check_phone(phone)
            timestamp = "out the business hour"
            prompt = f"""
            You are a scam detecting assistant. Given the timestamp is {timestamp} and the average valid score of {phone_score} from the phone preset fields pipeline {url_prompt}, and the content below, determine to what extent is this text conversation a safe message and provide 5 reasons for this conclusion.
            Please analyze the user's messages in a concise manner, following the format below.
            Classify each conversation as "SCAM", "SUSPICIOUS", or "SAFE" based on its content.
            Return valid JSON with keys: "sentiment" (SCAM, SUSPICIOUS, or SAFE), "alert_needed" (true/false), and "explanation" (5 bullet points for the conclusion).
            Note that for sentiment key, the only three options are "SCAM", "SUSPICIOUS", or "SAFE".
            Note that for explanation key, you MUST output 5 sentences of reasonings.
            Analyze these chat messages briefly and respond *only* with JSON.
         
            Messages:
            {messages_text}
            """
        elif email:
            email_checker = EmailCheck()
            email_score = email_checker.check_email(email)
            prompt = f"""
            You are a scam detecting assistant. Given the timestamp is in {timestamp} and the average valid score of {email_score} from the email preset fields pipeline {url_prompt}, and the content below, determine to what extent is this text conversation a safe message and provide 5 reasons for this conclusion.
            Please analyze the user's messages in a concise manner, following the format below.
            Classify each conversation as "SCAM", "SUSPICIOUS", or "SAFE" based on its content.
            Return valid JSON with keys: "sentiment" (SCAM, SUSPICIOUS, or SAFE), "alert_needed" (true/false), and "explanation" (5 sentences).
            Note that for sentiment key, the only three options are "SCAM", "SUSPICIOUS", or "SAFE".
            Note that for explanation key, you MUST output 5 sentences of reasonings.
            Analyze these chat messages briefly and respond *only* with JSON.
         
            Messages:
            {messages_text}
            """
        # logger.info(f"Email Check:{EmailCheck().check_email('georgepan900530@gmail.com')}")
        # logger.info(f"URL Check:{UrlCheck().check_url('https://www.google.com')}")
        # logger.info(f"Phone Check:{PhoneCheck().check_phone('14158586273')}")

        logger.debug(f"Prompt length: {len(prompt)}")
        logger.debug(f"Prompt:\n{prompt}")

        # Generate completion with timeout
        logger.info("Starting response generation...")
        try:
            with redirect_metal_output(), timeout(60):  # 30 second timeout
                response = first_guardian(
                    model="deepseek-r1:8b",
                    # model="llama3.2:latest",
                    prompt=prompt,
                )
                # response = llm(
                #     prompt=prompt,
                #     max_tokens=128,  # Reduced max tokens
                #     temperature=0.0,  # Lower temperature
                #     echo=False,
                #     # Removed default "stop" sequences to avoid immediate cut-off:
                #     # stop=["</s>", "\n\n"],
                #     stream=False,
                # )
                logger.debug(f"Raw response received: {response}")

        except TimeoutException:
            logger.error("Model inference timed out after 30 seconds")
            return SentimentResponse(
                sentiment="ERROR",
                alert_needed=False,
                explanation="Model inference timed out",
            )

        # Process response
        try:
            logger.info(response)
            # result = response["choices"][0]["text"].strip()
            result = response
            logger.info(result)
            # Try to locate JSON within the result
            import re

            match = re.search(r"\{.*\}", result, re.DOTALL)
            if not match:
                logger.error("No JSON object found in the response.")
                return SentimentResponse(
                    sentiment="SUSPICIOUS",
                    alert_needed=True,
                    explanation="Failed to find JSON block in model response.",
                )

            json_str = match.group(0)  # The substring that *should* be valid JSON
            logger.info(f"json_str:{json_str}")
            parsed_result = json.loads(json_str)
            return SentimentResponse(**parsed_result)

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error processing response: {str(e)}")
            return SentimentResponse(
                sentiment="SUSPICIOUS",
                alert_needed=True,
                explanation="Failed to parse model response. Defaulting to suspicious for safety.",
            )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return SentimentResponse(
            sentiment="ERROR",
            alert_needed=False,
            explanation=f"Failed to generate response: {str(e)}",
        )
