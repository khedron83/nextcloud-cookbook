package com.cubicserenity.nextcloudcookbook.ui.mealplanner

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil3.compose.AsyncImage
import com.cubicserenity.nextcloudcookbook.domain.model.RecipeSummary
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale

private val ISO = DateTimeFormatter.ISO_LOCAL_DATE
private val SHORT_DATE = DateTimeFormatter.ofPattern("d MMM")
private val DAY_NUM = DateTimeFormatter.ofPattern("d")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MealPlannerScreen(
    modifier: Modifier = Modifier,
    onRecipeClick: (Int) -> Unit = {},
    viewModel: MealPlannerViewModel = hiltViewModel(),
) {
    val weekStart by viewModel.weekStart.collectAsStateWithLifecycle()
    val entries by viewModel.entries.collectAsStateWithLifecycle()
    val recipes by viewModel.recipes.collectAsStateWithLifecycle()

    var pickerState by remember { mutableStateOf<Pair<LocalDate, String>?>(null) }

    val today = LocalDate.now()
    val days = (0..6).map { weekStart.plusDays(it.toLong()) }
    val endDate = weekStart.plusDays(6)
    val weekLabel = "${weekStart.format(SHORT_DATE)} – ${endDate.format(SHORT_DATE)} ${endDate.year}"
    val entryMap = remember(entries) { entries.associateBy { it.date to it.meal } }

    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = { Text("Meal Planner") },
            )
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            // Week nav
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = viewModel::prevWeek) { Icon(Icons.Default.ChevronLeft, "Previous") }
                Text(weekLabel, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f), textAlign = androidx.compose.ui.text.style.TextAlign.Center)
                IconButton(onClick = viewModel::nextWeek) { Icon(Icons.Default.ChevronRight, "Next") }
                TextButton(onClick = viewModel::goToday) { Text("Today") }
            }
            HorizontalDivider()

            // Scrollable week grid (vertical + horizontal)
            Box(
                Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState()),
            ) {
                Row(
                    Modifier.horizontalScroll(rememberScrollState()),
                ) {
                    days.forEach { day ->
                        val isToday = day == today
                        Column(
                            modifier = Modifier.width(140.dp).padding(4.dp),
                            verticalArrangement = Arrangement.spacedBy(4.dp),
                        ) {
                            // Day header
                            Surface(
                                color = if (isToday) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
                                shape = MaterialTheme.shapes.small,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Column(Modifier.padding(6.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text(
                                        day.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault()),
                                        style = MaterialTheme.typography.labelSmall,
                                        fontWeight = FontWeight.Bold,
                                        color = if (isToday) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                    Text(
                                        day.format(DAY_NUM),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = if (isToday) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                            // Meal slots
                            MEALS.forEach { meal ->
                                val entry = entryMap[day.format(ISO) to meal]
                                MealSlot(
                                    meal = meal,
                                    entry = entry?.recipeName,
                                    recipeId = entry?.recipeId,
                                    imageUrl = entry?.let { viewModel.thumbnailUrl(it.recipeId) },
                                    onAssign = { pickerState = day to meal },
                                    onClear = { viewModel.clear(day, meal) },
                                    onRecipeClick = onRecipeClick,
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    // Recipe picker dialog
    pickerState?.let { (day, meal) ->
        RecipePickerDialog(
            recipes = recipes,
            onPick = { recipe ->
                viewModel.assign(day, meal, recipe)
                pickerState = null
            },
            onDismiss = { pickerState = null },
        )
    }

}

@Composable
private fun MealSlot(
    meal: String,
    entry: String?,
    recipeId: Int?,
    imageUrl: String?,
    onAssign: () -> Unit,
    onClear: () -> Unit,
    onRecipeClick: (Int) -> Unit,
) {
    ElevatedCard(
        onClick = { recipeId?.let(onRecipeClick) },
        modifier = Modifier.fillMaxWidth().defaultMinSize(minHeight = 70.dp),
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            if (imageUrl != null) {
                AsyncImage(
                    model = imageUrl,
                    contentDescription = entry,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxWidth().height(72.dp),
                )
            }
            Column(Modifier.padding(6.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(meal, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.secondary, fontWeight = FontWeight.Bold)
                if (entry != null) {
                    Text(entry, style = MaterialTheme.typography.bodySmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        TextButton(onClick = onAssign, contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp)) {
                            Text("Change", style = MaterialTheme.typography.labelSmall)
                        }
                        IconButton(onClick = onClear, modifier = Modifier.size(20.dp)) {
                            Icon(Icons.Default.Close, "Remove", modifier = Modifier.size(14.dp), tint = MaterialTheme.colorScheme.error)
                        }
                    }
                } else {
                    TextButton(onClick = onAssign, contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp)) {
                        Icon(Icons.Default.Add, null, Modifier.size(14.dp))
                        Spacer(Modifier.width(2.dp))
                        Text("Add", style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        }
    }
}

@Composable
private fun RecipePickerDialog(
    recipes: List<RecipeSummary>,
    onPick: (RecipeSummary) -> Unit,
    onDismiss: () -> Unit,
) {
    var query by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf<String?>(null) }
    val categories = remember(recipes) {
        recipes.map { it.category }.filter { it.isNotBlank() }.distinct().sorted()
    }
    val filtered = remember(query, selectedCategory, recipes) {
        recipes
            .let { list -> if (selectedCategory != null) list.filter { it.category == selectedCategory } else list }
            .let { list -> if (query.isBlank()) list else list.filter { query.lowercase() in it.name.lowercase() } }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Pick a Recipe") },
        text = {
            Column {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    placeholder = { Text("Search…") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    leadingIcon = { Icon(Icons.Default.Search, null) },
                )
                if (categories.isNotEmpty()) {
                    Spacer(Modifier.height(6.dp))
                    LazyRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        contentPadding = PaddingValues(horizontal = 2.dp),
                    ) {
                        item {
                            FilterChip(
                                selected = selectedCategory == null,
                                onClick = { selectedCategory = null },
                                label = { Text("All") },
                            )
                        }
                        items(categories) { cat ->
                            FilterChip(
                                selected = selectedCategory == cat,
                                onClick = { selectedCategory = if (selectedCategory == cat) null else cat },
                                label = { Text(cat) },
                            )
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                LazyColumn(modifier = Modifier.height(300.dp)) {
                    items(filtered, key = { it.id }) { r ->
                        Surface(onClick = { onPick(r) }, modifier = Modifier.fillMaxWidth()) {
                            ListItem(
                                headlineContent = { Text(r.name) },
                                supportingContent = if (r.category.isNotBlank()) ({ Text(r.category, style = MaterialTheme.typography.labelSmall) }) else null,
                                colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.surface),
                            )
                        }
                        HorizontalDivider()
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
