// src/api.js

const BASE_URL = "http://127.0.0.1:8000"; // FastAPI backend

export async function negotiatePrice(product) {
  try {
    const res = await fetch(`${BASE_URL}/negotiate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(product),
    });
    return await res.json();
  } catch (err) {
    console.error("negotiatePrice error:", err);
    return { error: err.message };
  }
}

export async function moderateChat(message) {
  try {
    const res = await fetch(`${BASE_URL}/moderate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    return await res.json();
  } catch (err) {
    console.error("moderateChat error:", err);
    return { error: err.message };
  }
}
