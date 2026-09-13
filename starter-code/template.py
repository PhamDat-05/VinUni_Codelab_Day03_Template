"""Lab #3: a small, local ReAct-style travel assistant."""
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from tools import TOOL_MAP


class ChatbotBaseline:
    """A baseline which intentionally never looks up tool data."""
    def query(self, user_input: str) -> Dict[str, Any]:
        return {"status": "success", "answer": f"[Chatbot Baseline] Generic reply for: {user_input}", "tool_calls": []}


class ReActAgent:
    """Thought -> Action -> Observation agent using the lab's local tools."""
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.trace: List[Dict[str, Any]] = []

    def run(self, user_input: str) -> Dict[str, Any]:
        self.trace = []
        plan = self._make_plan(user_input)
        if not plan:
            answer = self._faq_answer(user_input)
            self.trace.append({"iteration": 1, "thought": "No tool is needed.", "action": None, "observation": None, "final_answer": answer})
            return self._result("completed", answer)

        observations: List[Tuple[str, Any]] = []
        for iteration, (name, args) in enumerate(plan, start=1):
            if iteration > self.max_iterations:
                return self._max_iterations_result()
            action = {"name": name, "args": args}
            observation = self._execute_action(action)
            self.trace.append({"iteration": iteration, "thought": f"Use {name} to get authoritative local data.", "action": action, "observation": observation})
            observations.append((name, observation))
            if len(plan) == 1:
                answer = self._format_answer(observations)
                self.trace[-1]["final_answer"] = answer
                return self._result("completed", answer)

        if len(self.trace) >= self.max_iterations:
            return self._max_iterations_result()
        answer = self._format_answer(observations)
        self.trace.append({"iteration": len(self.trace) + 1, "thought": "All required observations are available.", "action": None, "observation": None, "final_answer": answer})
        return self._result("completed", answer)

    def _make_plan(self, user_input: str) -> List[Tuple[str, Dict[str, Any]]]:
        text = user_input.lower()
        codes = re.findall(r"\b[A-Z]{3}\b", user_input.upper())
        plan: List[Tuple[str, Dict[str, Any]]] = []
        wants_flight = any(word in text for word in ("chuy\u1ebfn bay", "v\u00e9", "flight"))
        route = re.search(r"(?:\u0074\u1eeb|from)\s*([a-z]{3})\s*(?:\u0111\u0069|to|\u0111\u1ebfn)\s*([a-z]{3})", text)
        if wants_flight and route:
            plan.append(("get_flight_info", {"origin": route.group(1).upper(), "destination": route.group(2).upper(), "max_price": self._extract_max_price(text)}))
        if any(word in text for word in ("th\u1eddi ti\u1ebft", "m\u1eb7c g\u00ec", "trang ph\u1ee5c", "weather")):
            city = self._weather_city(text, codes, plan)
            if city:
                plan.append(("get_weather_forecast", {"city_code": city}))
        return plan

    @staticmethod
    def _extract_max_price(text: str) -> int:
        match = re.search(r"(?:d\u01b0\u1edbi|under|max)\s*(\d+(?:[.,]\d+)?)\s*(?:tri\u1ec7u|million)", text)
        return int(float(match.group(1).replace(",", ".")) * 1_000_000) if match else 5_000_000

    @staticmethod
    def _weather_city(text: str, codes: List[str], plan: List[Tuple[str, Dict[str, Any]]]) -> Optional[str]:
        for code in ("SGN", "HAN", "DAD"):
            if code in codes:
                return code
        if "\u0111\u00e0 n\u1eb5ng" in text or "da nang" in text:
            return "DAD"
        if "h\u00e0 n\u1ed9i" in text or "ha noi" in text:
            return "HAN"
        if "h\u1ed3 ch\u00ed minh" in text or "ho chi minh" in text:
            return "SGN"
        return plan[0][1]["destination"] if plan else None

    @staticmethod
    def _execute_action(action: Dict[str, Any]) -> Any:
        try:
            name, args = str(action["name"]).strip().lower(), action["args"]
            if not isinstance(args, dict):
                raise ValueError("args must be a JSON object")
        except (KeyError, TypeError, ValueError) as exc:
            return {"error": f"Invalid JSON format: {exc}"}
        tool = TOOL_MAP.get(name)
        if tool is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return tool(**args)
        except (TypeError, ValueError) as exc:
            return {"error": str(exc)}

    def _result(self, status: str, answer: str) -> Dict[str, Any]:
        return {"status": status, "answer": answer, "iterations": len(self.trace), "trace": self.trace}

    def _max_iterations_result(self) -> Dict[str, Any]:
        return self._result("max_iterations_reached", "Kh\u00f4ng th\u1ec3 ho\u00e0n th\u00e0nh trong s\u1ed1 b\u01b0\u1edbc t\u1ed1i \u0111a.")

    @staticmethod
    def _format_answer(observations: List[Tuple[str, Any]]) -> str:
        parts: List[str] = []
        for name, data in observations:
            if isinstance(data, dict) and "error" in data:
                parts.append(f"Lookup failed: {data['error']}.")
            elif name == "get_flight_info":
                if not data:
                    parts.append("No matching flights were found.")
                else:
                    flights = "; ".join(f"{f['flight_number']} ({f['airline']}, {f['departure_time']}, {f['price_vnd']:,} VND)" for f in data)
                    parts.append(f"Matching flights: {flights}.")
            elif name == "get_weather_forecast":
                parts.append(f"Weather in {data['city']}: {data['temperature_c']}\u00b0C, {data['condition']}. {data['recommendation']}")
        return " ".join(parts)

    @staticmethod
    def _faq_answer(user_input: str) -> str:
        return "Vinpearl support does not have policy data in this lab. Please confirm through an official channel: " + user_input


def main() -> None:
    query = "T\u00ecm chuy\u1ebfn bay t\u1eeb HAN \u0111i SGN d\u01b0\u1edbi 2 tri\u1ec7u, r\u1ed3i cho bi\u1ebft th\u1eddi ti\u1ebft SGN n\u00ean m\u1eb7c g\u00ec?"
    print(json.dumps(ReActAgent().run(query), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
