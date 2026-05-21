package com.example.commerceagent.app

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.commerceagent.ui.chat.ChatScreen
import com.example.commerceagent.ui.product.ProductDetailScreen
import com.example.commerceagent.ui.sessions.SessionListScreen

@Composable
fun AppNavGraph() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "sessions") {
        composable("sessions") {
            SessionListScreen(
                onOpenChat = { sessionId -> navController.navigate("chat/$sessionId") },
                onNewChat = { navController.navigate("chat/new") }
            )
        }
        composable(
            route = "chat/{sessionId}",
            arguments = listOf(navArgument("sessionId") { type = NavType.StringType })
        ) {
            ChatScreen(
                sessionId = it.arguments?.getString("sessionId")?.takeUnless { id -> id == "new" },
                onOpenProduct = { productId -> navController.navigate("product/$productId") },
                onBack = { navController.popBackStack() }
            )
        }
        composable(
            route = "product/{productId}",
            arguments = listOf(navArgument("productId") { type = NavType.StringType })
        ) {
            ProductDetailScreen(
                productId = it.arguments?.getString("productId").orEmpty(),
                onBack = { navController.popBackStack() }
            )
        }
    }
}
