import { useState } from "react";
import { negotiatePrice, moderateChat } from "./api";

function App() {
  const [product, setProduct] = useState({
    title: "",
    category: "",
    brand: "",
    condition: "",
    age_months: "age_months in numeric format",
    asking_price: "asking_price in numeric format",
    location: "",
  });
  const [priceResponse, setPriceResponse] = useState(null);

  const [chatMsg, setChatMsg] = useState("");
  const [chatHistory, setChatHistory] = useState([]);

  // Update product fields dynamically
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setProduct((prev) => ({
      ...prev,
      [name]: name === "age_months" || name === "asking_price" ? Number(value) : value
    }));
  };

  const handlePriceSuggest = async () => {
    try {
      const res = await negotiatePrice(product);
      setPriceResponse(res);
    } catch (err) {
      setPriceResponse({ fair_price_range: { display: "Error" }, reasoning: err.message });
    }
  };

  const formatAIMsg = (res) => {
    if (!res || !res.result) return "No response";
    const { status, reason, description, matches } = res.result;
    let text = `Status: ${status}\nReason: ${reason}\nDescription: ${description}`;
    if (matches) {
      const { phones, urls, profanity } = matches;
      if (phones?.length) text += `\nPhones detected: ${phones.join(", ")}`;
      if (urls?.length) text += `\nURLs detected: ${urls.join(", ")}`;
      if (profanity?.length) text += `\nProfanity: ${profanity.join(", ")}`;
    }
    return text;
  };

  const handleSendChat = async () => {
    if (!chatMsg.trim()) return;
    try {
      const res = await moderateChat(chatMsg);
      const aiText = formatAIMsg(res);
      setChatHistory([...chatHistory, { user: "You", text: chatMsg }, { user: "AI", text: aiText }]);
      setChatMsg("");
    } catch (err) {
      setChatHistory([...chatHistory, { user: "AI", text: "Error: " + err.message }]);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-6">Marketplace Assistant</h1>

      {/* Product Input Section */}
      <div className="bg-white p-4 rounded shadow mb-6">
        <h2 className="text-xl font-semibold mb-4">Product Details</h2>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <input name="title" value={product.title} onChange={handleInputChange} placeholder="Title" className="border p-2 rounded"/>
          <input name="category" value={product.category} onChange={handleInputChange} placeholder="Category" className="border p-2 rounded"/>
          <input name="brand" value={product.brand} onChange={handleInputChange} placeholder="Brand" className="border p-2 rounded"/>
          <input name="condition" value={product.condition} onChange={handleInputChange} placeholder="Condition (Good/Fair/Like New)" className="border p-2 rounded"/>
          <input name="age_months" type="number" value={product.age_months} onChange={handleInputChange} placeholder="Age (months)" className="border p-2 rounded"/>
          <input name="asking_price" type="number" value={product.asking_price} onChange={handleInputChange} placeholder="Asking Price" className="border p-2 rounded"/>
          <input name="location" value={product.location} onChange={handleInputChange} placeholder="Location" className="border p-2 rounded"/>
        </div>
        <button onClick={handlePriceSuggest} className="bg-blue-600 text-white px-4 py-2 rounded">Suggest Price</button>

        {priceResponse && (
          <div className="mt-4">
            <p><b>Fair Price:</b> {priceResponse.fair_price_range.display}</p>
            <p><b>Reason:</b> {priceResponse.reasoning}</p>
          </div>
        )}
      </div>

      {/* Chat Section */}
      <div className="bg-white p-4 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">Chat Moderation</h2>
        <div className="h-60 overflow-y-auto border p-2 mb-4">
          {chatHistory.map((msg, i) => (
            <div key={i} className="mb-2">
              <p><b>{msg.user}:</b></p>
              <pre className="bg-gray-100 p-2 rounded whitespace-pre-wrap">{msg.text}</pre>
            </div>
          ))}
        </div>
        <div className="flex">
          <input value={chatMsg} onChange={(e) => setChatMsg(e.target.value)} placeholder="Type a message..." className="flex-1 border p-2 rounded-l"/>
          <button onClick={handleSendChat} className="bg-green-600 text-white px-4 py-2 rounded-r">Send</button>
        </div>
      </div>
    </div>
  );
}

export default App;
