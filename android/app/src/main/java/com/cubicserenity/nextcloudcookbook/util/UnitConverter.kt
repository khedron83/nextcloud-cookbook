package com.cubicserenity.nextcloudcookbook.util

import kotlin.math.abs
import kotlin.math.round

private val unicodeFracs = mapOf(
    '½' to 0.5, '⅓' to 1.0/3, '⅔' to 2.0/3,
    '¼' to 0.25, '¾' to 0.75,
    '⅛' to 0.125, '⅜' to 0.375, '⅝' to 0.625, '⅞' to 0.875,
)

private val numPat = """(?:\d+\s+\d+/\d+|\d+/\d+|\d+\.?\d*|[½⅓⅔¼¾⅛⅜⅝⅞]|\d+[½⅓⅔¼¾⅛⅜⅝⅞])"""

private val volumeUnits = listOf(
    Regex("""($numPat)\s*(?:fl\.?\s*oz\.?|fluid\s+ounces?)\b""", RegexOption.IGNORE_CASE) to 29.574,
    Regex("""($numPat)\s*cups?\b""", RegexOption.IGNORE_CASE) to 240.0,
    Regex("""($numPat)\s*(?:tbsps?|tablespoons?)\b""", RegexOption.IGNORE_CASE) to 15.0,
    Regex("""($numPat)\s*(?:tsps?|teaspoons?)\b""", RegexOption.IGNORE_CASE) to 5.0,
    Regex("""($numPat)\s*(?:pints?|pts?)(?!\w)\b""", RegexOption.IGNORE_CASE) to 473.176,
    Regex("""($numPat)\s*(?:quarts?|qts?)(?!\w)\b""", RegexOption.IGNORE_CASE) to 946.353,
    Regex("""($numPat)\s*(?:gallons?|gals?)(?!\w)\b""", RegexOption.IGNORE_CASE) to 3785.41,
)

private val weightUnits = listOf(
    Regex("""($numPat)\s*(?:lbs?\.?|pounds?)\b""", RegexOption.IGNORE_CASE) to 453.592,
    Regex("""($numPat)\s*(?:oz\.?|ounces?)\b""", RegexOption.IGNORE_CASE) to 28.3495,
)

private fun parseQty(s: String): Double? {
    val trimmed = s.trim()
    unicodeFracs[trimmed.lastOrNull()]?.let { frac ->
        val prefix = trimmed.dropLast(1)
        if (prefix.isEmpty()) return frac
        prefix.toDoubleOrNull()?.let { return it + frac }
    }
    Regex("""^(\d+)\s+(\d+)/(\d+)$""").matchEntire(trimmed)?.let {
        val (a, b, c) = it.destructured
        return a.toDouble() + b.toDouble() / c.toDouble()
    }
    Regex("""^(\d+)/(\d+)$""").matchEntire(trimmed)?.let {
        val (a, b) = it.destructured
        return a.toDouble() / b.toDouble()
    }
    return trimmed.toDoubleOrNull()
}

private fun fmtVol(ml: Double) = when {
    ml >= 950 -> "${(ml / 1000).let { if (it == it.toLong().toDouble()) it.toLong() else "%.1f".format(it) }} L"
    ml >= 10 -> "${(round(ml / 5) * 5).toInt()} ml"
    else -> "${"%.1f".format(ml)} ml"
}

private fun fmtWt(g: Double) = when {
    g >= 950 -> "${(g / 1000).let { if (it == it.toLong().toDouble()) it.toLong() else "%.1f".format(it) }} kg"
    g >= 10 -> "${(round(g / 5) * 5).toInt()} g"
    else -> "${"%.1f".format(g)} g"
}

fun convertIngredient(text: String): String {
    var result = text
    for ((regex, factor) in volumeUnits) {
        result = regex.replace(result) { m ->
            parseQty(m.groupValues[1])?.let { fmtVol(it * factor) } ?: m.value
        }
    }
    for ((regex, factor) in weightUnits) {
        result = regex.replace(result) { m ->
            parseQty(m.groupValues[1])?.let { fmtWt(it * factor) } ?: m.value
        }
    }
    return result
}

fun convertInstruction(text: String): String =
    Regex("""(\d+)\s*°?\s*F\b""", RegexOption.IGNORE_CASE).replace(text) { m ->
        val f = m.groupValues[1].toDouble()
        val c = (round(((f - 32) * 5 / 9) / 5) * 5).toInt()
        "${c}°C"
    }

private fun fmtScaled(value: Double): String {
    if (value <= 0) return "0"
    for (den in listOf(2, 3, 4, 8)) {
        val num = round(value * den).toInt()
        if (abs(num.toDouble() / den - value) < 0.04) {
            val g = gcd(num, den)
            val n = num / g; val d = den / g
            if (d == 1) return n.toString()
            val whole = n / d; val rem = n % d
            return if (whole > 0) "$whole $rem/$d" else "$rem/$d"
        }
    }
    return if (value >= 10) "%.0f".format(value)
    else "%.2f".format(value).trimEnd('0').trimEnd('.')
}

private fun gcd(a: Int, b: Int): Int = if (b == 0) a else gcd(b, a % b)

fun scaleIngredient(text: String, factor: Double): String {
    if (abs(factor - 1.0) < 0.001) return text
    val m = Regex("""^(\s*)($numPat)(.*)""", setOf(RegexOption.DOT_MATCHES_ALL)).find(text) ?: return text
    val qty = parseQty(m.groupValues[2]) ?: return text
    return m.groupValues[1] + fmtScaled(qty * factor) + m.groupValues[3]
}
