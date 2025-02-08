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
import re
from tkinter import messagebox
import tkinter as tk

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from API_check.email_check import EmailCheck
from API_check.url_check import UrlCheck
from API_check.phone_check import PhoneCheck

# Add this near the top of the file, after imports
parent_monitor = None


def register_parent_monitor(monitor):
    global parent_monitor
    parent_monitor = monitor


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


def load_scammer_timestamp():
    try:
        with open("./../config.json", "r") as f:
            config = json.load(f)
            if config.get("scammer_timestamp"):
                return config.get("scammer_timestamp")
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

        messages_text = chats[0].message
        phone = None
        if load_scammer_phone():
            phone = load_scammer_phone()
        if load_scammer_email():
            email = load_scammer_email()
        if load_scammer_timestamp():
            timestamp = load_scammer_timestamp()

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
        if phone:
            phone_checker = PhoneCheck()
            score = phone_checker.check_phone(phone_number=phone)

            # Convert timestamp (assumed format "HH:MM") into an integer hour.
            try:
                hour = int(timestamp.split(":")[0])
            except Exception as e:
                logger.error(f"Failed to parse timestamp to integer: {e}")
                # Set default hour or handle the error as needed.
                hour = 0
            if hour > 17 or hour < 9:
                timestamp_text = "out of the business hour"
            else:
                timestamp_text = "in the business hour"

            logger.info(f"timestamp_text: {timestamp_text}")

            initial_prompt = f"""
            You are a scam detecting assistant. Given the timestamp is {timestamp_text}, the average valid phone score of {score} from the preset fields pipeline {url_prompt}, and the message content below, determine to what extent is this text conversation a safe message and provide the entire thought process behind this conclusion.
            Please analyze the user's messages in a concise manner, following the format below.\n\n
            Classify each conversation as "SCAM", "SUSPICIOUS", or "SAFE" based on its content.
            Return valid JSON with keys: "sentiment" (SCAM, SUSPICIOUS, or SAFE), "alert_needed" (true/false), and "explanation".
            Note that for sentiment key, the only three options are "SCAM", "SUSPICIOUS", or "SAFE".  Analyze these chat messages briefly and respond *only* with JSON.\n\n
            Messages:\n\n
            {messages_text}
            """
        else:
            email_checker = EmailCheck()
            score = email_checker.check_email(email=None)
            # Convert timestamp (assumed format "HH:MM") into an integer hour.
            try:
                hour = int(timestamp.split(":")[0])
            except Exception as e:
                logger.error(f"Failed to parse timestamp to integer: {e}")
                # Set default hour or handle the error as needed.
                hour = 0
            if hour > 17 or hour < 9:
                timestamp_text = "out of the business hour"
            else:
                timestamp_text = "in the business hour"
            initial_prompt = f"""
            You are a scam detecting assistant. Given the timestamp is {timestamp_text}, the average valid email score of {score} from the preset fields pipeline {url_prompt}, and the message content below, determine to what extent is this text conversation a safe message and provide the entire thought process behind this conclusion.
            Please analyze the user's messages in a concise manner, following the format below.\n\n
            Classify each conversation as "SCAM", "SUSPICIOUS", or "SAFE" based on its content.
            Return valid JSON with keys: "sentiment" (SCAM, SUSPICIOUS, or SAFE), "alert_needed" (true/false), and "explanation".
            Note that for sentiment key, the only three options are "SCAM", "SUSPICIOUS", or "SAFE".  Analyze these chat messages briefly and respond *only* with JSON.\n\n
            Messages:\n\n
            {messages_text}
            """

        reason_valid = None
        for i in range(6):
            # Generate completion with timeout
            logger.info("Starting response generation...")
            if i == 0:  # it is the first iteration
                prompt = initial_prompt
            else:
                add_on_prompt = f"""
                The scam detecting result validator has validated your conclusion and determined it is incorrect for the {i}th time. 
                Please reconsider your initial answer and provide another response.\n\n
                """
                prompt = add_on_prompt + initial_prompt
                # logger.info(f"prompt:{prompt}")
            try:
                with redirect_metal_output(), timeout(60):  # 30 second timeout
                    response = first_guardian(
                        model="deepseek-r1:8b",
                        # model="llama3.2:latest",
                        prompt=prompt,
                    )

            except TimeoutException:
                logger.error("Model inference timed out after 30 seconds")
                return SentimentResponse(
                    sentiment="ERROR",
                    alert_needed=False,
                    explanation="Model inference timed out",
                )

            # Process response
            try:
                result = response
                match = re.search(r"\{.*\}", result, re.DOTALL)
                if not match:
                    logger.error("No JSON object found in the response.")
                    return SentimentResponse(
                        sentiment="SUSPICIOUS",
                        alert_needed=True,
                        explanation="Failed to find JSON block in model response.",
                    )

                json_str = match.group(0)  # The substring that *should* be valid JSON
                parsed_result = json.loads(json_str)
                explanation, sentiment = (
                    parsed_result["explanation"],
                    parsed_result["sentiment"],
                )
                second_prompt = f"""
                You are a scam detecting result validator. From this previous conclusion of a scam detector:\n\n{explanation}\n\nConsider the thought process and the following content related to the message: The timestamp is {timestamp}, 
                the average valid phone or email score of {score} from the preset fields pipeline {url_prompt}.
                Please analyze the previous detector's reasonings and determine its validity.
                Classify the reasoning for the conversation as "VALID" or "INVALID".
                Return valid JSON with keys: "valid" (True or False).
                Note that for valid key, the only options are True or False.
                """

                reason_valid = second_guardian(
                    model="deepseek-r1:8b",
                    prompt=second_prompt,
                    first_output=explanation,
                    status=sentiment,
                )
                logger.info(f"current iteration: {i}, reason_valid: {reason_valid}")

                if reason_valid:
                    logger.info(f"The reason is valid, returning the result")
                    return SentimentResponse(**parsed_result)
                else:
                    logger.info(f"Invalid analysis result, retrying (attempt {i+1})...")
                    continue

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"Error processing response: {str(e)}")
                return SentimentResponse(
                    sentiment="SUSPICIOUS",
                    alert_needed=True,
                    explanation="Failed to parse model response. Defaulting to suspicious for safety.",
                )

        # if the reason is not valid after 4 iterations, return SUSPICIOUS
        parsed_result = {
            "sentiment": "SUSPICIOUS",
            "alert_needed": True,
            "explanation": "Failed to find valid reason after 4 iterations, marking as suspicious",
        }
        logger.info(
            f"After 4 iterations, the reason is not valid, returning SUSPICIOUS"
        )
        return SentimentResponse(**parsed_result)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return SentimentResponse(
            sentiment="ERROR",
            alert_needed=False,
            explanation=f"Failed to generate response: {str(e)}",
        )
