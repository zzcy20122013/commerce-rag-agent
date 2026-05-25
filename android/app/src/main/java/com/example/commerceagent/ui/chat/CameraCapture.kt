package com.example.commerceagent.ui.chat

import java.io.File

fun createCameraImageFile(cacheDir: File): File {
    val cameraDir = File(cacheDir, "camera").apply { mkdirs() }
    return File(cameraDir, "capture_${System.currentTimeMillis()}.jpg")
}
