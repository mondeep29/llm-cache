from pathlib import Path

PAIRS = [
    # paraphrases — should_hit
    ("hit-001", "paraphrase", True, "What is your return policy for electronics?", "How do I return an electronic item I bought?"),
    ("hit-002", "paraphrase", True, "How do I reset my password?", "I forgot my password, how can I reset it?"),
    ("hit-003", "paraphrase", True, "What are the shipping options to the United States?", "Which delivery methods do you offer for US orders?"),
    ("hit-004", "paraphrase", True, "Summarize the plot of Pride and Prejudice.", "Give me a short summary of Pride and Prejudice."),
    ("hit-005", "paraphrase", True, "Explain photosynthesis in simple terms.", "Can you describe how photosynthesis works like I'm a beginner?"),
    ("hit-006", "paraphrase", True, "How do I convert a Python list to a set?", "What's the Python code to turn a list into a set?"),
    ("hit-007", "paraphrase", True, "What time does the library close on weekdays?", "When is the library's weekday closing time?"),
    ("hit-008", "paraphrase", True, "Is the restaurant open on Thanksgiving?", "Does the restaurant operate on Thanksgiving Day?"),
    ("hit-009", "paraphrase", True, "How can I cancel my subscription?", "I want to stop my subscription, what are the steps?"),
    ("hit-010", "paraphrase", True, "What is the capital of France?", "Which city is the capital of France?"),
    ("hit-011", "paraphrase", True, "Write a polite email declining a meeting.", "Draft a courteous email to say I can't attend the meeting."),
    ("hit-012", "paraphrase", True, "How do I boil pasta so it isn't mushy?", "What's the right way to cook pasta al dente?"),
    ("hit-013", "paraphrase", True, "List three benefits of daily walking.", "Name three advantages of walking every day."),
    ("hit-014", "paraphrase", True, "What does HTTP 429 mean?", "Explain the HTTP 429 status code."),
    ("hit-015", "paraphrase", True, "How do I connect to a PostgreSQL database from Python?", "Show me how Python can connect to Postgres."),
    ("hit-016", "paraphrase", True, "Translate 'good morning' into Spanish.", "What's the Spanish phrase for good morning?"),
    ("hit-017", "paraphrase", True, "How often should I water a succulent?", "What's a good watering schedule for succulents?"),
    ("hit-018", "paraphrase", True, "What is the difference between RAM and storage?", "Explain RAM versus disk storage."),
    ("hit-019", "paraphrase", True, "Give me a 20-minute beginner yoga routine.", "Suggest a short yoga sequence for beginners that takes about 20 minutes."),
    ("hit-020", "paraphrase", True, "How do I change a flat bicycle tire?", "Walk me through replacing a punctured bike tire."),
    ("hit-021", "paraphrase", True, "What ingredients are in a classic margarita?", "How do you make a traditional margarita?"),
    ("hit-022", "paraphrase", True, "Explain what a mutex is in concurrent programming.", "What does a mutex do when multiple threads run?"),
    ("hit-023", "paraphrase", True, "How can I reduce blue light from my monitor at night?", "Tips for lowering screen blue light in the evening."),
    ("hit-024", "paraphrase", True, "What is the boiling point of water at sea level?", "At what temperature does water boil at sea level?"),
    ("hit-025", "paraphrase", True, "How do I request a refund for a delayed flight?", "What's the process for getting a refund when my flight is delayed?"),
    ("hit-026", "paraphrase", True, "Write a SQL query to count users by country.", "How would I count the number of users grouped by country in SQL?"),
    ("hit-027", "paraphrase", True, "What are symptoms of a mild concussion?", "List common signs of a mild concussion."),
    ("hit-028", "paraphrase", True, "How do I enable two-factor authentication?", "Steps to turn on 2FA on my account."),
    ("hit-029", "paraphrase", True, "Recommend a weekend trip from Boston under $200.", "Suggest a cheap weekend getaway leaving from Boston, budget around 200 dollars."),
    ("hit-030", "paraphrase", True, "What does git rebase do compared to merge?", "Explain git rebase versus git merge."),
    ("hit-031", "paraphrase", True, "How do I defrost chicken safely?", "What's a safe way to thaw frozen chicken?"),
    ("hit-032", "paraphrase", True, "Explain overfitting in machine learning.", "What does it mean when a model overfits?"),
    ("hit-033", "paraphrase", True, "How do I apply for a library card?", "What do I need to get a library card?"),
    ("hit-034", "paraphrase", True, "What is the warranty period for this laptop?", "How long is the laptop warranty?"),
    ("hit-035", "paraphrase", True, "Give a high-level overview of TCP handshake.", "Describe the TCP three-way handshake simply."),
    ("hit-036", "paraphrase", True, "How do I clean a stainless steel pan?", "What's the best way to wash a stainless steel skillet?"),
    ("hit-037", "paraphrase", True, "What time zone is Denver in?", "Which time zone does Denver, Colorado use?"),
    ("hit-038", "paraphrase", True, "Write a unit test for a Python function that adds two numbers.", "Show a pytest example testing an add function."),
    ("hit-039", "paraphrase", True, "How do I pack a carry-on for a 3-day trip?", "What should I put in a carry-on bag for three days?"),
    ("hit-040", "paraphrase", True, "Explain the difference between HTTP GET and POST.", "When should I use GET versus POST in HTTP?"),
    # near-misses — should_miss (look similar, different intent)
    ("miss-001", "near_miss", False, "What is your return policy for electronics?", "What is your return policy for groceries?"),
    ("miss-002", "near_miss", False, "How do I reset my password?", "How do I reset my two-factor authentication?"),
    ("miss-003", "near_miss", False, "What are the shipping options to the United States?", "What are the shipping options to Canada?"),
    ("miss-004", "near_miss", False, "Summarize the plot of Pride and Prejudice.", "Summarize the plot of Sense and Sensibility."),
    ("miss-005", "near_miss", False, "Explain photosynthesis in simple terms.", "Explain cellular respiration in simple terms."),
    ("miss-006", "near_miss", False, "How do I convert a Python list to a set?", "How do I convert a Python list to a tuple?"),
    ("miss-007", "near_miss", False, "What time does the library close on weekdays?", "What time does the library close on Sundays?"),
    ("miss-008", "near_miss", False, "Is the restaurant open on Thanksgiving?", "Is the restaurant open on Christmas?"),
    ("miss-009", "near_miss", False, "How can I cancel my subscription?", "How can I pause my subscription for a month?"),
    ("miss-010", "near_miss", False, "What is the capital of France?", "What is the capital of Spain?"),
    ("miss-011", "near_miss", False, "Write a polite email declining a meeting.", "Write a polite email accepting a meeting."),
    ("miss-012", "near_miss", False, "How do I boil pasta so it isn't mushy?", "How do I boil rice so it isn't mushy?"),
    ("miss-013", "near_miss", False, "List three benefits of daily walking.", "List three benefits of daily running."),
    ("miss-014", "near_miss", False, "What does HTTP 429 mean?", "What does HTTP 404 mean?"),
    ("miss-015", "near_miss", False, "How do I connect to a PostgreSQL database from Python?", "How do I connect to a MySQL database from Python?"),
    ("miss-016", "near_miss", False, "Translate 'good morning' into Spanish.", "Translate 'good morning' into French."),
    ("miss-017", "near_miss", False, "How often should I water a succulent?", "How often should I water a fern?"),
    ("miss-018", "near_miss", False, "What is the difference between RAM and storage?", "What is the difference between CPU and GPU?"),
    ("miss-019", "near_miss", False, "Give me a 20-minute beginner yoga routine.", "Give me a 20-minute beginner pilates routine."),
    ("miss-020", "near_miss", False, "How do I change a flat bicycle tire?", "How do I change a flat car tire?"),
    ("miss-021", "near_miss", False, "What ingredients are in a classic margarita?", "What ingredients are in a classic mojito?"),
    ("miss-022", "near_miss", False, "Explain what a mutex is in concurrent programming.", "Explain what a semaphore is in concurrent programming."),
    ("miss-023", "near_miss", False, "How can I reduce blue light from my monitor at night?", "How can I reduce brightness from my monitor at night?"),
    ("miss-024", "near_miss", False, "What is the boiling point of water at sea level?", "What is the freezing point of water at sea level?"),
    ("miss-025", "near_miss", False, "How do I request a refund for a delayed flight?", "How do I request a refund for a cancelled hotel?"),
    ("miss-026", "near_miss", False, "Write a SQL query to count users by country.", "Write a SQL query to count orders by country."),
    ("miss-027", "near_miss", False, "What are symptoms of a mild concussion?", "What are symptoms of a mild migraine?"),
    ("miss-028", "near_miss", False, "How do I enable two-factor authentication?", "How do I disable two-factor authentication?"),
    ("miss-029", "near_miss", False, "Recommend a weekend trip from Boston under $200.", "Recommend a weekend trip from Boston under $2000."),
    ("miss-030", "near_miss", False, "What does git rebase do compared to merge?", "What does git reset do compared to revert?"),
    ("miss-031", "near_miss", False, "How do I defrost chicken safely?", "How do I defrost salmon safely?"),
    ("miss-032", "near_miss", False, "Explain overfitting in machine learning.", "Explain underfitting in machine learning."),
    ("miss-033", "near_miss", False, "How do I apply for a library card?", "How do I apply for a credit card?"),
    ("miss-034", "near_miss", False, "What is the warranty period for this laptop?", "What is the warranty period for this phone?"),
    ("miss-035", "near_miss", False, "Give a high-level overview of TCP handshake.", "Give a high-level overview of TLS handshake."),
    ("miss-036", "near_miss", False, "How do I clean a stainless steel pan?", "How do I clean a cast iron pan?"),
    ("miss-037", "near_miss", False, "What time zone is Denver in?", "What time zone is Phoenix in?"),
    ("miss-038", "near_miss", False, "Write a unit test for a Python function that adds two numbers.", "Write a unit test for a Python function that multiplies two numbers."),
    ("miss-039", "near_miss", False, "How do I pack a carry-on for a 3-day trip?", "How do I pack a checked bag for a 3-week trip?"),
    ("miss-040", "near_miss", False, "Explain the difference between HTTP GET and POST.", "Explain the difference between HTTP PUT and PATCH."),
    # clearly unrelated
    ("unrel-001", "unrelated", False, "What is your return policy for electronics?", "How do I train a golden retriever puppy?"),
    ("unrel-002", "unrelated", False, "How do I reset my password?", "What is the score of last night's basketball game?"),
    ("unrel-003", "unrelated", False, "Explain photosynthesis in simple terms.", "Write a haiku about subway delays."),
    ("unrel-004", "unrelated", False, "How do I convert a Python list to a set?", "What wine pairs well with grilled salmon?"),
    ("unrel-005", "unrelated", False, "What is the capital of France?", "How do I change the oil in a 2015 Honda Civic?"),
    ("unrel-006", "unrelated", False, "Give me a 20-minute beginner yoga routine.", "Debug why my Kubernetes pod is CrashLooping."),
    ("unrel-007", "unrelated", False, "How do I enable two-factor authentication?", "What is the recipe for sourdough starter?"),
    ("unrel-008", "unrelated", False, "Explain overfitting in machine learning.", "Where can I see cherry blossoms in Washington DC?"),
]


def main() -> None:
    payload = {
        "pairs": [
            {
                "id": pid,
                "category": category,
                "should_hit": should_hit,
                "canonical": canonical,
                "query": query,
            }
            for pid, category, should_hit, canonical, query in PAIRS
        ]
    }
    import json

    out = Path(__file__).with_name("prompt_pairs.json")
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['pairs'])} pairs to {out}")


if __name__ == "__main__":
    main()
