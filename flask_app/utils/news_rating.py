import json
import os
import openai
from typing import List, Dict, Union, Tuple, Any


class NewsRating:
    """
    Třída pro zpracování a hodnocení zpráv o akciích.
    Zpracovává JSON řetězce obsahující zprávy, kontroluje jejich počet a délku,
    a následně je odesílá do OpenAI API pro hodnocení.
    """

    def __init__(self):
        """
        Inicializace třídy NewsRating.
        API klíč je načten z proměnné prostředí OPEN_AI_API_KEY.
        """
        # Načtení API klíče z proměnné prostředí
        self.api_key = os.environ.get("OPEN_AI_API_KEY")
        if not self.api_key:
            raise ValueError("API klíč není nastaven v proměnné prostředí OPEN_AI_API_KEY")

        # Konfigurace OpenAI klienta
        openai.api_key = self.api_key

        # Nastavení limitů a modelu
        self.max_news_count = 10
        self.max_news_length = 1000
        self.openai_model = "gpt-4o-mini"

    def parse_json_news(self, json_string: str) -> List[str]:
        """
        Načte JSON řetězec a extrahuje z něj seznam zpráv.

        Args:
            json_string (str): JSON řetězec obsahující zprávy

        Returns:
            List[str]: Seznam extrahovaných zpráv

        Raises:
            ValueError: Pokud je JSON neplatný
        """
        try:
            news_data = json.loads(json_string)
            # Očekáváme, že news_data je seznam řetězců
            if not isinstance(news_data, list):
                raise ValueError("JSON data musí být seznam")

            return news_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Neplatný JSON formát: {e}")

    def check_news_count(self, news_list: List[str]) -> bool:
        """
        Zkontroluje, zda počet zpráv nepřekračuje maximální limit.

        Args:
            news_list (List[str]): Seznam zpráv

        Returns:
            bool: True pokud počet zpráv nepřekračuje limit, jinak False
        """
        return len(news_list) <= self.max_news_count

    def check_news_length(self, news_list: List[str]) -> bool:
        """
        Zkontroluje, zda délka každé zprávy nepřekračuje maximální limit.

        Args:
            news_list (List[str]): Seznam zpráv

        Returns:
            bool: True pokud délka všech zpráv nepřekračuje limit, jinak False
        """
        for news in news_list:
            if len(news) > self.max_news_length:
                return False
        return True

    def validate_news(self, news_list: List[str]) -> Tuple[bool, bool]:
        """
        Provede kontrolu počtu zpráv a délky každé zprávy.

        Args:
            news_list (List[str]): Seznam zpráv

        Returns:
            Tuple[bool, bool]: (count_valid, length_valid) - zda počet a délka zpráv vyhovují limitům
        """
        count_valid = self.check_news_count(news_list)
        length_valid = self.check_news_length(news_list)
        return count_valid, length_valid

    def limit_news_count(self, news_list: List[str]) -> List[str]:
        """
        Omezí počet zpráv na maximální povolený limit.

        Args:
            news_list (List[str]): Seznam zpráv

        Returns:
            List[str]: Seznam zpráv omezený na maximální počet
        """
        return news_list[:self.max_news_count]

    def truncate_news(self, news_list: List[str]) -> List[str]:
        """
        Zkrátí každou zprávu na maximální povolenou délku.

        Args:
            news_list (List[str]): Seznam zpráv

        Returns:
            List[str]: Seznam zpráv s omezenou délkou
        """
        return [news[:self.max_news_length] for news in news_list]

    def process_news(self, json_string: str) -> List[str]:
        """
        Zpracuje JSON řetězec, zkontroluje a upraví zprávy podle limitů.

        Args:
            json_string (str): JSON řetězec obsahující zprávy

        Returns:
            List[str]: Seznam zpracovaných zpráv respektujících limity
        """
        # Načtení zpráv z JSON
        news_list = self.parse_json_news(json_string)

        # Kontrola počtu a délky zpráv
        count_valid, length_valid = self.validate_news(news_list)

        # Aplikace limitů pokud je to nutné
        if not count_valid:
            news_list = self.limit_news_count(news_list)

        if not length_valid:
            news_list = self.truncate_news(news_list)

        return news_list

    def call_openai_api(self, news_list: List[str]) -> Dict[str, Any]:
        """
        Odešle zprávy do OpenAI API pro hodnocení pomocí oficiální OpenAI knihovny.

        Args:
            news_list (List[str]): Seznam zpráv k hodnocení

        Returns:
            Dict[str, Any]: Odpověď z OpenAI API

        Raises:
            Exception: Pokud dojde k chybě při komunikaci s API
        """
        # Sestavení promptu pro OpenAI
        prompt = """
        Please analyze the following stock market news articles. Rate each article on a scale from 0 to 10 based on its investment implications:
        - 0 = Immediately sell the stock
        - 5 = Hold the stock in portfolio
        - 10 = Buy more of the stock

        Provide your ratings in a JSON format with article indices as keys and scores as values. Only return the JSON without any explanations.

        Example output format:
        {
          "0": 7.5,
          "1": 3.2,
          ...
        }

        Here are the articles to analyze:
        """

        # Přidání zpráv do promptu s indexy
        for i, news in enumerate(news_list):
            prompt += f"\n{i}: {news}"

        try:
            # Volání OpenAI API pomocí oficiální knihovny
            response = openai.ChatCompletion.create(
                model=self.openai_model,
                messages=[
                    {"role": "system",
                     "content": "You are a financial analyst specialized in stock market news evaluation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0  # Deterministický výstup
            )

            return response
        except Exception as e:
            raise Exception(f"Chyba při komunikaci s OpenAI API: {e}")

    def parse_openai_response(self, api_response: Dict[str, Any]) -> Dict[int, float]:
        """
        Zpracuje odpověď z OpenAI API a extrahuje hodnocení.

        Args:
            api_response (Dict[str, Any]): Odpověď z OpenAI API

        Returns:
            Dict[int, float]: Slovník s indexy zpráv a jejich hodnoceními

        Raises:
            ValueError: Pokud se nepodaří extrahovat hodnocení z odpovědi
        """
        try:
            # Získání obsahu odpovědi (upraveno pro oficiální knihovnu)
            content = api_response["choices"][0]["message"]["content"]

            # Extrakce JSON z odpovědi (může být obalen dalším textem)
            # Hledáme část textu mezi { a }
            start_idx = content.find('{')
            end_idx = content.rfind('}')

            if start_idx == -1 or end_idx == -1:
                raise ValueError("JSON nenalezen v odpovědi OpenAI API")

            json_str = content[start_idx:end_idx + 1]
            ratings_data = json.loads(json_str)

            # Převedení klíčů ze stringů na inty a hodnot na float
            ratings = {int(k): float(v) for k, v in ratings_data.items()}

            return ratings
        except (KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Chyba při zpracování odpovědi OpenAI API: {e}")

    def calculate_average_rating(self, ratings: Dict[int, float]) -> float:
        """
        Vypočítá průměrné hodnocení ze všech zpráv.

        Args:
            ratings (Dict[int, float]): Slovník s hodnoceními jednotlivých zpráv

        Returns:
            float: Průměrné hodnocení zaokrouhlené na 2 desetinná místa
        """
        if not ratings:
            return 0.0

        total = sum(ratings.values())
        average = total / len(ratings)

        # Zaokrouhlení na 2 desetinná místa
        return round(average, 2)

    def rate_news(self, json_string: str) -> float:
        """
        Hlavní metoda, která zpracuje JSON řetězec se zprávami,
        odešle je do OpenAI API a vrátí průměrné hodnocení.

        Args:
            json_string (str): JSON řetězec obsahující zprávy

        Returns:
            float: Průměrné hodnocení zpráv

        Raises:
            Exception: Pokud dojde k chybě během zpracování
        """
        try:
            # Zpracování a úprava zpráv
            processed_news = self.process_news(json_string)

            # Pokud nejsou žádné zprávy k hodnocení
            if not processed_news:
                return 0.0

            # Volání OpenAI API
            api_response = self.call_openai_api(processed_news)

            # Zpracování odpovědi
            ratings = self.parse_openai_response(api_response)

            # Výpočet průměrného hodnocení
            average_rating = self.calculate_average_rating(ratings)

            return average_rating
        except Exception as e:
            # Logování chyby a propagace výjimky dále
            print(f"Chyba při hodnocení zpráv: {e}")
            raise