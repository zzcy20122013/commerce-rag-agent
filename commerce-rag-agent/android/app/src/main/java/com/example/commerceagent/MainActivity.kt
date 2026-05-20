package com.example.commerceagent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.example.commerceagent.app.CommerceAgentApp
import com.example.commerceagent.theme.CommerceAgentTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CommerceAgentTheme {
                CommerceAgentApp()
            }
        }
    }
}
