package com.example.commerceagent.ui.chat

import kotlin.test.Test
import kotlin.test.assertEquals

class VoiceInputFormatterTest {
    @Test
    fun voiceTranscriptFillsEmptyInput() {
        assertEquals("推荐 300 以内通勤鞋", mergeVoiceTranscript("", " 推荐 300 以内通勤鞋 "))
    }

    @Test
    fun voiceTranscriptAppendsToExistingInput() {
        assertEquals(
            "我想买鞋 推荐 300 以内通勤鞋",
            mergeVoiceTranscript("我想买鞋", "推荐 300 以内通勤鞋")
        )
    }
}
