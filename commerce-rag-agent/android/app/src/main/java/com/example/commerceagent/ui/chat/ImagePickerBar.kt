package com.example.commerceagent.ui.chat

import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig

@Composable
fun ImagePickerBar(
    previewUrl: String?,
    onPickImage: () -> Unit
) {
    Row {
        AssistChip(
            onClick = onPickImage,
            label = { Text(if (previewUrl == null) "添加图片" else "已添加图片") }
        )
        if (previewUrl != null) {
            AsyncImage(
                model = ApiConfig.BASE_URL + previewUrl,
                contentDescription = "已上传图片",
                modifier = Modifier
                    .padding(start = 10.dp)
                    .width(48.dp)
                    .height(48.dp)
            )
            Text(
                text = "将随消息一起检索相似商品",
                modifier = Modifier.padding(start = 10.dp, top = 10.dp)
            )
        }
    }
}
