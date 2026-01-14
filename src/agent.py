from dotenv import load_dotenv
import litellm

from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart
from a2a.utils import get_message_text, new_agent_text_message
import json
load_dotenv()


class Agent:
    def __init__(self):
        self.messages = []

    # async def run(self, message: Message, updater: TaskUpdater) -> None:
    #     input_text = get_message_text(message)
    #     print(f"> {input_text}")

    #     await updater.update_status(
    #         TaskState.working, new_agent_text_message("Thinking...")
    #     )

    #     self.messages.append({"content": input_text, "role": "user"})
    #     completion = litellm.completion(
    #         model="gpt-4o",
    #         messages=self.messages
    #     )
    #     response = completion.choices[0].message.content
    #     self.messages.append({"content": response, "role": "assistant"})
    #     print(response)

    #     await updater.add_artifact(
    #         parts=[Part(root=TextPart(text=response))],
    #         name="Response",
    #     )
    def __init__(self):
        api_key = "AIzaSyDomhyXZ4F-SjoN8FKCvDWK4IkWW39p2vg"
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None


    async def run(self, message_text: str, updater: TaskUpdater) -> None:
            await updater.update_status(
                TaskState.working, new_agent_text_message("Analyzing tables...")
            )

            try:
                request = json.loads(message_text)
                tables = request.get("tables", [])
                task = request.get("task", "")
            except json.JSONDecodeError:
                await updater.add_artifact(
                    parts=[Part(root=TextPart(text='{"error": "Invalid JSON input"}'))],
                    name="Error",
                )
                return

            if self.model:
                # Use Gemini for analysis
                prompt = f"""You are a data engineer analyzing database tables.

    Given these tables:
    {json.dumps(tables, indent=2)}

    Task: {task}

    Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
    {{
        "primary_keys": {{"table_name": "column_name", ...}},
        "join_columns": [["table1.col", "table2.col"], ...],
        "inconsistencies": ["description of inconsistency 1", ...],
        "merged_schema": {{"unified_table_name": ["col1", "col2", ...]}}
    }}"""

                try:
                    response = self.model.generate_content(prompt)
                    result = response.text.strip()
                    # Clean up markdown if present
                    if result.startswith("```"):
                        result = result.split("```")[1]
                        if result.startswith("json"):
                            result = result[4:]
                        result = result.strip()
                except Exception as e:
                    result = json.dumps({"error": str(e)})
            else:
                # Fallback: return a reasonable static response
                result = json.dumps({
                    "primary_keys": {t["name"]: t["columns"][0] for t in tables},
                    "join_columns": [],
                    "inconsistencies": ["Unable to analyze without API key"],
                    "merged_schema": {"merged": [col for t in tables for col in t["columns"]]}
                })

            await updater.add_artifact(
                parts=[Part(root=TextPart(text=result))],
                name="Schema Analysis",
            )