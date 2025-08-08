# AI-Developer-Test- Radioactive Toxin
technical assessment for Hustlr Staffing Services

### 1. How to Run the App
Prerequisites:

• Python 3.8+ installed

• pip package manager

• Recommended: use a virtual environment to isolate dependencies

Steps:
• Clone or place the project folder on your machine.

• Open a terminal (or PyCharm terminal) in the project folder.

• Create and activate a virtual environment:

  • "python -m venv .venv"
  
  • ".venv\Scripts\Activate" # Activate (Windows PowerShell)
  
  • "source .venv/bin/activate" # Activate (macOS/Linux)

• Install dependencies: pip install flask rapidfuzz

• Run the application: python app.py

• The app will start on: http://127.0.0.1:5000/

Testing the app:
Once the app is running on http://127.0.0.1:5000/, open these URLs in your browser.

Test examples:

### Basic Tests:

• List all categories: http://127.0.0.1:5000/categories

• Simple keyword search (balanced mode): http://127.0.0.1:5000/search?q=running+shoes

### Adding Price & Rating Filters:

• Price filter only: http://127.0.0.1:5000/search?q=running+shoes+under+$100

• Minimum rating filter only: http://127.0.0.1:5000/search?q=headphones+4+stars

• Combined price & rating filters: http://127.0.0.1:5000/search?q=camping+tent+under+$200+4+stars

### Category Detection:

• Implicit category detection: http://127.0.0.1:5000/search?q=novel+books

• Explicit category keyword: http://127.0.0.1:5000/search?q=electronics+best+rated

### Switching Ranking Modes:

You can switch using query parameters or natural language keywords.

• Balanced mode (default): http://127.0.0.1:5000/search?q=running+shoes

• Rating mode via query parameter: http://127.0.0.1:5000/search?q=running+shoes&mode=rating

• Rating mode via natural language trigger: http://127.0.0.1:5000/search?q=running+shoes+best+rated

• Cheap mode via query parameter: http://127.0.0.1:5000/search?q=running+shoes&mode=cheap

• Cheap mode via natural language trigger: http://127.0.0.1:5000/search?q=cheapest+running+shoes

• Multiple filters + rating mode: http://127.0.0.1:5000/search?q=camping+tent+under+$150+4+stars&mode=rating

• Multiple filters + cheap mode: http://127.0.0.1:5000/search?q=wireless+headphones+under+$200+cheapest

2. AI Feature Chosen

• Smart Product Search (NLP)

• Uses natural language processing to parse user queries for:

• Price ranges (e.g., "under $100", "between $50 and $150")

• Minimum rating (e.g., "4 stars", "best rated")

• Category detection (e.g., "running shoes", "headphones")

• Keywords for fuzzy matching

• Allows dynamic ranking mode Switching:

  • Balanced (default/relevance + rating + price): ?mode=balanced

  • Highest rated/Rating-focused: ?mode=rating or include keywords like “best rated”

  • Cheapest/Price-focused ("cheap mode"): ?mode=cheap or include keywords like “cheapest”

3.Tools/Libraries Used
  
  • Flask: lightweight Python web framework for building the API
  
  • RapidFuzz: high-performance fuzzy string matching for text relevance scoring

  • Python Standard Library-json, re for data loading and regex parsing

4.Notable Assumptions

• Ratings are on a 0-5 scale.

• Price is stored as a numeric float or integer.

• Categories in queries are matched case-insensitively against known product categories, 

• with a few keyword-based fallbacks (e.g., “shoes” to Footwear).

• No external AI API keys (e.g., OpenAI) are used-the search is entirely local and deterministic.

• This is a development setup using Flask’s built-in server.
