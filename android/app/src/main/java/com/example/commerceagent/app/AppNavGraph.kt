package com.example.commerceagent.app

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.commerceagent.ui.auth.LoginScreen
import com.example.commerceagent.ui.checkout.CheckoutScreen
import com.example.commerceagent.ui.main.MainScreen
import com.example.commerceagent.ui.orders.OrdersScreen
import com.example.commerceagent.ui.product.ProductDetailScreen

@Composable
fun AppNavGraph() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "login") {
        composable("login") {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate("main") {
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }
        composable("main") {
            MainScreen(
                onOpenProduct = { productId -> navController.navigate("product/$productId") },
                onOpenOrders = { navController.navigate("orders") },
                onOpenCheckout = { navController.navigate("checkout") },
                onLogout = {
                    navController.navigate("login") {
                        popUpTo("main") { inclusive = true }
                    }
                }
            )
        }
        composable("orders") {
            OrdersScreen(onBack = { navController.popBackStack() })
        }
        composable("checkout") {
            CheckoutScreen(
                onBack = { navController.popBackStack() },
                onSubmitted = {
                    navController.navigate("orders") {
                        popUpTo("checkout") { inclusive = true }
                    }
                }
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
