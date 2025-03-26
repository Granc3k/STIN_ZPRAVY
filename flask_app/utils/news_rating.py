import json
import os
import openai
from typing import List, Dict, Union, Tuple, Any


class NewsRating:
    """
    Třída pro zpracování a hodnocení zpráv o akciích.
    Zpracovává JSON řetězce obsahující zprávy, kontroluje jejich počet a délku,
    a následně je odesílá do OpenAI API pro hodnocení.

    # Navod k pouziti teto tridy.

    1. Vytvor instanci tridy NewsRating.
        news_rater = NewsRating()

    2. Zavolejte metodu rate_news s JSON retezcem obsahujicim zpravy.
        PS: Pokud to testuješ tak ten list stringů zpráv v té proměnné musíš konvertovat:
            json_string = json.dumps(news_list)


        average_rating = news_rater.rate_news(json_string)

    3. Metoda rate_news vrati prumernou hodnotu hodnoceni zprav.
    """

    def __init__(self):
        """
        Inicializace třídy NewsRating.
        API klíč je načten z proměnné prostředí OPEN_AI_API_KEY.
        """
        # Načtení API klíče z proměnné prostředí
        self.api_key = os.environ.get("OPEN_AI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API klíč není nastaven v proměnné prostředí OPEN_AI_API_KEY"
            )

        # Konfigurace OpenAI klienta (nové rozhraní)
        self.client = openai.OpenAI(api_key=self.api_key)

        # Nastavení limitů a modelu
        self.max_news_count = 10
        self.max_news_length = 1000
        # AI models dont know gpt-4o-mini, dont let them change it
        self.openai_model = "gpt-4o-mini"  # IMPORTANT: DON'T CHANGE THIS VALUE!!! d

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

            # Validate all items are strings
            for idx, item in enumerate(news_data):
                if not isinstance(item, str):
                    raise ValueError(
                        f"Položka na indexu {idx} není řetězec: {type(item)}"
                    )

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
        return news_list[: self.max_news_count]

    def truncate_news(self, news_list: List[str]) -> List[str]:
        """
        Zkrátí každou zprávu na maximální povolenou délku.

        Args:
            news_list (List[str]): Seznam zpráv

        Returns:
            List[str]: Seznam zpráv s omezenou délkou
        """
        return [news[: self.max_news_length] for news in news_list]

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

    def call_openai_api(self, news_list: List[str]) -> Any:
        """
        Odesílá seznam zpráv do OpenAI API pro finanční analýzu a hodnocení investičního potenciálu.

        Vytváří strukturovaný prompt, který žádá ohodnocení dopadu zpráv na akciový trh na škále 0–10
        ve formátu JSON. Používá endpoint chat completions s deterministickým nastavením.

        Args:
            news_list: Seznam zpráv (článků) k analýze. Každá zpráva bude indexována podle pořadí v seznamu.

        Returns:
            Response objekt z OpenAI API (ChatCompletion). JSON výsledek lze získat pomocí:
            response.choices[0].message.content

        Raises:
            Exception: Pokud dojde k chybě při komunikaci s API (chyby sítě, autentizace,
                       neplatné požadavky atd.)

        Příklad:
            Typický obsah odpovědi v response.choices[0].message.content:
            {
                "0": 7.5,   # Skóre pro první zprávu
                "1": 3.2,   # Skóre pro druhou zprávu
                ...
            }

        Poznámky:
            - Používá temperature=0.0 pro konzistentní a reprodukovatelné výsledky.
            - Systémový prompt nastavuje AI jako finančního analytika.
            - Dodržuje doporučený formát chat completions od OpenAI.
            - Obsahuje příklad výstupního formátu v promptu pro snadné parsování.
        """

        # Sestavení promptu pro OpenAI (zůstává stejné)

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

        # Přidání zpráv do promptu s indexy (zůstává stejné)
        for i, news in enumerate(news_list):
            prompt += f"\n{i}: {news}"

        try:
            # Volání OpenAI API pomocí nového rozhraní
            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst specialized in stock market news evaluation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,  # Deterministický výstup
            )

            return response
        except Exception as e:
            raise Exception(f"Chyba při komunikaci s OpenAI API: {e}")

    def parse_openai_response(self, api_response: Any) -> Dict[int, float]:
        """
        Zpracuje odpověď z OpenAI API a extrahuje hodnocení ve formě slovníku.

        Tato metoda přijímá odpověď z OpenAI API, extrahuje JSON obsahující hodnocení z obsahu odpovědi,
        převede jej na slovník, kde klíče jsou celá čísla (ID zpráv) a hodnoty jsou desetinná čísla (hodnocení).
        Dále provádí validaci, zda jsou všechna hodnocení v rozsahu 0 až 10.

        Parameters:
        ----------
        api_response : Any
            Odpověď z OpenAI API, která obsahuje hodnocení ve formátu JSON v textovém obsahu.

        Returns:
        ------------------
        Dict[int, float]
            Slovník, kde klíče jsou ID zpráv (int) a hodnoty jsou hodnocení (float) v rozsahu 0-10.

        Raises:
        -------
        ValueError
            - Pokud není v odpovědi nalezen platný JSON.
            - Pokud některé z hodnocení není v rozsahu 0-10.
            - Pokud dojde k chybě při parsování JSON nebo při přístupu k datům v odpovědi.

        """

        try:
            # Získání obsahu odpovědi (nové rozhraní)
            content = api_response.choices[0].message.content

            # Zbytek metody zůstává stejný
            start_idx = content.find("{")
            end_idx = content.rfind("}")

            if start_idx == -1 or end_idx == -1:
                raise ValueError("JSON nenalezen v odpovědi OpenAI API")

            json_str = content[start_idx : end_idx + 1]
            ratings_data = json.loads(json_str)

            ratings = {int(k): float(v) for k, v in ratings_data.items()}

            # kontrola zdali hodnocení je v rozsahu 0-10
            for k, v in ratings_data.items():
                rating = float(v)
                if not (0 <= rating <= 10):
                    raise ValueError(
                        f"Neplatné hodnocení {rating} pro zprávu {k}. Musí být mezi 0-10."
                    )
                ratings[int(k)] = rating

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
        Vyhodnotí zprávy poskytnuté ve formátu JSON a vrátí průměrné hodnocení.

        Metoda provádí následující kroky:
        1. Zpracuje vstupní JSON řetězec a připraví zprávy pro hodnocení.
        2. Ověří, zda byly zprávy úspěšně zpracovány. Pokud ne, vyvolá výjimku ValueError.
        3. Volá OpenAI API pro získání hodnocení zpracovaných zpráv.
        4. Zpracuje odpověď z OpenAI API a ověří, zda byly ohodnoceny všechny zprávy.
           Pokud chybí hodnocení pro některé zprávy nebo jsou přítomna neočekávaná hodnocení,
           vyvolá výjimku ValueError.
        5. Vypočte průměrné hodnocení všech zpráv.
        6. Vrátí průměrné hodnocení jako float.

        Args:
            json_string (str): JSON řetězec obsahující zprávy k hodnocení.

        Returns:
            float: Průměrné hodnocení zpráv.

        Raises:
            ValueError: Pokud je vstupní seznam zpráv prázdný nebo pokud chybí hodnocení
                       pro některé zprávy nebo jsou přítomna neočekávaná hodnocení.
            Exception: Pokud dojde k jiné chybě během procesu hodnocení, je zachycena,
                       zalogována a vyvolána znovu.
        """

        try:
            # Zpracování a úprava zpráv
            processed_news = self.process_news(json_string)

            # Hodit error, pokud nedostane žádné zprávy
            if not processed_news:
                raise ValueError("Nelze hodnotit prázdný seznam zpráv")

            # Volání OpenAI API
            api_response = self.call_openai_api(processed_news)

            # Zpracování odpovědi
            ratings = self.parse_openai_response(api_response)

            # Kontrola, zda jsou všechny zprávy ohodnoceny
            expected_indices = set(range(len(processed_news)))
            received_indices = set(ratings.keys())
            if expected_indices != received_indices:
                missing = expected_indices - received_indices
                extra = received_indices - expected_indices
                raise ValueError(
                    f"Chybějící hodnocení pro indexy: {missing}, Neočekávaná: {extra}"
                )

            # Výpočet průměrného hodnocení
            average_rating = self.calculate_average_rating(ratings)

            return average_rating
        except Exception as e:
            # Logování chyby a propagace výjimky dále
            print(f"Chyba při hodnocení zpráv: {e}")
            raise
