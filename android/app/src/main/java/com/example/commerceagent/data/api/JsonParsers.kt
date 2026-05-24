package com.example.commerceagent.data.api

import com.example.commerceagent.data.model.ProductCard
import com.example.commerceagent.data.model.ProductEvidence
import com.example.commerceagent.data.model.ProductDetail
import com.example.commerceagent.data.model.Cart
import com.example.commerceagent.data.model.CartItem
import com.example.commerceagent.data.model.CartProduct
import com.example.commerceagent.data.model.CheckoutResult
import com.example.commerceagent.data.model.Session
import com.example.commerceagent.data.model.SessionMessage
import org.json.JSONArray
import org.json.JSONObject

fun JSONObject.toProductCard(): ProductCard {
    val reasonsJson = optJSONArray("reasons") ?: JSONArray()
    val evidenceJson = optJSONArray("evidence") ?: JSONArray()
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
        score = optDouble("score"),
        evidence = List(evidenceJson.length()) { index ->
            evidenceJson.optJSONObject(index).toProductEvidence()
        },
        sourceSummary = optString("source_summary")
    )
}

private fun JSONObject?.toProductEvidence(): ProductEvidence {
    val json = this ?: JSONObject()
    return ProductEvidence(
        source = json.optString("source"),
        text = json.optString("text")
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

fun JSONObject.toCart(): Cart {
    val itemsJson = optJSONArray("items") ?: JSONArray()
    return Cart(
        items = List(itemsJson.length()) { index -> itemsJson.getJSONObject(index).toCartItem() },
        total = optInt("total")
    )
}

fun JSONObject.toCheckoutResult(): CheckoutResult {
    val orderIdsJson = optJSONArray("order_ids") ?: JSONArray()
    val itemsJson = optJSONArray("items") ?: JSONArray()
    return CheckoutResult(
        orderIds = List(orderIdsJson.length()) { index -> orderIdsJson.optString(index) },
        items = List(itemsJson.length()) { index -> itemsJson.getJSONObject(index).toCartItem() },
        total = optInt("total"),
        cart = (optJSONObject("cart") ?: JSONObject()).toCart()
    )
}

private fun JSONObject.toCartItem(): CartItem {
    val productJson = optJSONObject("product") ?: JSONObject()
    return CartItem(
        id = optString("id"),
        quantity = optInt("quantity"),
        subtotal = optInt("subtotal"),
        product = CartProduct(
            id = productJson.optString("id"),
            title = productJson.optString("title"),
            price = productJson.optInt("price"),
            stock = productJson.optInt("stock"),
            imageUrl = productJson.optString("image_url")
        )
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
