package com.cubicserenity.nextcloudcookbook.util

fun parseDurationMinutes(iso: String): Int {
    if (iso.isBlank()) return 0
    var total = 0
    val h = Regex("(\\d+)H").find(iso)?.groupValues?.get(1)?.toIntOrNull() ?: 0
    val m = Regex("(\\d+)M").find(iso)?.groupValues?.get(1)?.toIntOrNull() ?: 0
    val s = Regex("(\\d+)S").find(iso)?.groupValues?.get(1)?.toIntOrNull() ?: 0
    total += h * 60 + m + s / 60
    return total
}

fun minutesToDuration(minutes: Int): String {
    if (minutes <= 0) return ""
    val h = minutes / 60
    val m = minutes % 60
    return "PT" + (if (h > 0) "${h}H" else "") + (if (m > 0) "${m}M" else "")
}

fun formatMinutes(minutes: Int): String {
    if (minutes <= 0) return ""
    val h = minutes / 60
    val m = minutes % 60
    return when {
        h > 0 && m > 0 -> "${h}h ${m}m"
        h > 0 -> "${h}h"
        else -> "${m}m"
    }
}
