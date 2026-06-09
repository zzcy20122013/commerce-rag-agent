package com.example.commerceagent.data.api

import kotlin.test.Test
import kotlin.test.assertEquals

class UploadApiTest {
    @Test
    fun jpegBytesUseJpegUploadMetadata() {
        val metadata = detectUploadImageMetadata(
            bytes = byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte(), 0xE0.toByte()),
            declaredContentType = "image/png"
        )

        assertEquals("upload.jpg", metadata.fileName)
        assertEquals("image/jpeg", metadata.contentType)
    }

    @Test
    fun pngBytesUsePngUploadMetadata() {
        val metadata = detectUploadImageMetadata(
            bytes = byteArrayOf(
                0x89.toByte(),
                0x50,
                0x4E,
                0x47,
                0x0D,
                0x0A,
                0x1A,
                0x0A
            ),
            declaredContentType = null
        )

        assertEquals("upload.png", metadata.fileName)
        assertEquals("image/png", metadata.contentType)
    }
}
