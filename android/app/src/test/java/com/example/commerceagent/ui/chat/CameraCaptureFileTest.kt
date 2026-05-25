package com.example.commerceagent.ui.chat

import java.io.File
import kotlin.io.path.createTempDirectory
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class CameraCaptureFileTest {
    @Test
    fun createsCameraImageFileUnderCameraCacheDirectory() {
        val cacheDir = createTempDirectory(prefix = "commerce-camera-test").toFile()

        val file = createCameraImageFile(cacheDir)

        assertEquals(File(cacheDir, "camera"), file.parentFile)
        assertTrue(file.name.startsWith("capture_"))
        assertTrue(file.name.endsWith(".jpg"))
    }
}
