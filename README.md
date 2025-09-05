

## AI-powered assistant for a second-hand marketplace.  
It provides **fair price suggestions** and **chat moderation** using LLMs + agents.  
Built with **FastAPI (backend)**, **React (frontend)**, **LangChain**, **Gemini API**, and **SerpAPI**.

---

## 🚀 Features

### 🔹 Agent 1 – Price Suggestor
- Input: Product details (title, category, brand, condition, age in months, asking price, location).
- Applies:
  - Category-based depreciation.
  - Product age adjustment.
  - Condition multiplier (`Like New`, `Good`, `Fair`).
  - Brand & location adjustment.
- Output:
  ```json
  {
    "fair_price_range": { "min": 17350, "max": 25200, "currency": "INR", "display": "₹17,350 - ₹25,200" },
    "reasoning": "Depreciation + condition + brand/location adjustments",
    "confidence": "medium",
    "Comaparables": Comparison with olx, shopify, flipkart or online shopping sites,
  }

### Bonus:
 Fetches comparable prices from OLX/Cashify (via SerpAPI).

### 🔹 Agent 2 – Chat Moderation
* Input: A chat message between buyer and seller.

* Detects:

        Abusive or toxic messages.

        Spam/scams.

        Personal information (mobile numbers, emails).

* Output:

  ```json
  {
    "status": "Abusive",
    "reason": "Contains insulting language",
    "description": Describing the message in chat and reason about it and status of it,
  }

### 🔹 API Endpoints
    POST /negotiate → Price Suggestor Agent

    POST /moderate → Chat Moderation Agent

### Swagger UI available at → http://127.0.0.1:8000/docs

### 🔹 Frontend (React + Tailwind)
* Price Suggestion UI → Enter product details, get fair price + reasoning.

* Chat Moderation UI → Chat interface showing user + AI moderation responses.

* Chat history stored locally (simple simulated conversation).

### 🛠️ Tech Stack
* Backend: FastAPI, Python 3.10+, LangChain, Gemini API, SerpAPI (optional).

* Frontend: React (Vite), TailwindCSS.

* LLMs: Gemini API (fast inference), OpenAI/HuggingFace optional.

* Extras: BeautifulSoup (OLX scraping), Requests.

### ⚙️ Setup & Installation
#### 1️⃣ Clone the Repository
  ```bash
    git clone https://github.com/your-username/marketplace-assistant.git
    cd marketplace-assistant
```
#### 2️⃣ Backend Setup (FastAPI)
  ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate   # (Windows: venv\Scripts\activate)
    pip install -r requirements.txt
  ```
#### 🔑 Environment Variables
Create a .env file inside backend/:

```ini
GEMINI_API_KEY=your_gemini_api_key
SERPAPI_API_KEY=your_serpapi_key   # optional
```
#### Run Backend
```bash
uvicorn main:app --reload
```
Backend will run on → http://127.0.0.1:8000


#### 3️⃣ Frontend Setup (React + Vite + Tailwind)
```bash
cd frontend
npm install
npm run dev
```
Frontend will run on → http://localhost:5173

### 🖥️ Usage
#### ✅ Price Suggestion
```bash
curl -X POST http://127.0.0.1:8000/negotiate \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "title": "iPhone 12 128GB",
    "category": "Mobile",
    "brand": "Apple",
    "condition": "Good",
    "age_months": 18,
    "asking_price": 45000,
    "location": "Delhi",
    "use_llm": true,
    "use_comparables": true
  }'
```
Response:

```json
{
    "fair_price_range": {
        "min": 25700,
        "max": 37000,
        "currency": "INR",
        "display": "₹25,700 - ₹37,000"
    },
    "reasoning": "The asking price of ₹45,000 for an 18-month-old iPhone 12 (128GB) in good condition is significantly higher than the fair price range of ₹25,700 to ₹37,000.  Since there are no comparable listings, this suggests the seller's price is inflated.  A more reasonable asking price would fall within or slightly above the heuristic range, perhaps ₹37,000 to ₹40,000.",
    "comparables": [olx - ₹27000, Shopify- ₹35000],
}
```
#### ✅ Chat Moderation
```bash
curl -X POST http://127.0.0.1:8000/moderate \
  -H "Content-Type: application/json" \
  -d '{"message":"Call me at 9876543210", "sender_role":"buyer"}'

  ```
Response:

```json
{
        "status": "Unsafe",
        "reason": "Message contains a phone number.",
        "description": "The message includes a phone number, which violates our policy against sharing personal contact information.  Please remove the phone number to continue.  This helps protect user privacy.",
        "matches": {
            "phones": [
                "9876543210",
            ]
        }
}
```
#### 🎯 Evaluation Mapping
* Agent Implementation → Price Suggestor & Chat Moderation implemented as independent agents.

* Correctness → Uses heuristics + LLM reasoning + comparables from OLX/Cashify.

* Code Quality → Modular, documented, separated into utils, backend, frontend.

* Practicality → Realistic for a marketplace.

* Creativity → Bonus features: Internet comparables, negotiation bot possible, moderation with reasoning.

📌 Bonus Ideas
🤝 Negotiation Bot between buyer & seller.

🚫 Fraud detection (flag suspicious listings).

📊 Dashboard of depreciation trends.

🗂️ Multi-agent orchestration with LangChain / LangGraph.
