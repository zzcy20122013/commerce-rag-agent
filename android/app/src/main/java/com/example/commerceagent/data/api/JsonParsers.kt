package com.example.commerceagent.data.api

import com.example.commerceagent.data.model.ProductCard
import com.example.commerceagent.data.model.ProductDetail
import com.example.commerceagent.data.model.Session
import com.example.commerceagent.data.model.SessionMessage
import org.json.JSONArray
import org.json.JSONObject

fun JSONObject.toProductCard(): ProductCard {
    val reasonsJson = optJSONArray("reasons") ?: JSONArray()
    return ProductCard(
        productId = optString("product_id"),
        title = optString("title"),
        subtitle = optString("subtitle"),
        price = optInt("price"),
        originalPrice = optInt("original_price", optInt("price")),
        imageUrl = optString("image_url"),
        rating = optDouble("rating"),
        sales = optInt("sales"),
        stockStatus = optString("stock_status"),
        reasons = List(reasonsJson.length()) { index -> reasonsJson.optString(index) },
        score = optDouble("score")
    )
}

fun JSONObject.toProductDetail(): ProductDetail {
    return ProductDetail(
        id = optString("id"),
        title = optString("title"),
        category = optString("category"),
        brand = optString("brand"),
        price = optInt("price"),
        description = optString("description"),
        rating = optDouble("rating"),
        sales = optInt("sales"),
        stock = optInt("stock"),
        imageUrl = optString("image_url")
    )
}

fun JSONObject.toSession(): Session {
    return Session(
        id = optString("id"),
        title = optString("title"),
        updatedAt = optString("updatedAt")
    )
}

fun JSONObject.toSessionMessage(): SessionMessage {
    val cardsJson = optJSONArray("productCards") ?: JSONArray()
    return SessionMessage(
        id = optString("id"),
        role = optString("role"),
        content = optString("content"),
        createdAt = optString("createdAt"),
        productCards = List(cardsJson.length()) { index -> cardsJson.getJSONObject(index).toProductCard() }
    )
}
