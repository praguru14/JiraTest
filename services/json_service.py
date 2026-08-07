import json


class JsonService:

    @staticmethod
    def parse_llm_json(response):

        response = response.strip()

        if response.startswith("```json"):
            response = response[7:]

        if response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        return json.loads(response)