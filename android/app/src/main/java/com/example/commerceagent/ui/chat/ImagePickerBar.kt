package com.example.commerceagent.ui.chat

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig

@Composable
fun ImagePickerBar(
    previewUrl: String?,
    onPickImage: () -> Unit
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        AssistChip(
            onClick = onPickImage,
            label = { Text(if (previewUrl == null) "添加图片" else "图片已添加") },
            shape = RoundedCornerShape(999.dp),
            border = BorderStroke(1.dp, Color(0xFFDCD2FF)),
            colors = AssistChipDefaults.assistChipColors(
                containerColor = Color(0xFFF7F3FF),
                labelColor = Color(0xFF5B35EA)
            )
        )
        if (previewUrl != null) {
            AsyncImage(
                model = ApiConfig.resolveUrl(previewUrl),
                contentDescription = "已上传图片",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .padding(start = 10.dp)
                    .width(46.dp)
                    .height(46.dp)
            )
            Text(
                text = "会随消息一起找相似商品",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.56f),
                modifier = Modifier.padding(start = 10.dp)
            )
        }
    }
}
