package com.cubicserenity.nextcloudcookbook.ui.detail

import android.app.Activity
import android.view.WindowManager
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil3.compose.AsyncImage
import com.cubicserenity.nextcloudcookbook.domain.model.Recipe
import com.cubicserenity.nextcloudcookbook.util.formatMinutes
import com.cubicserenity.nextcloudcookbook.util.parseDurationMinutes

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun RecipeDetailScreen(
    recipeId: Int,
    onBack: () -> Unit,
    onEdit: () -> Unit,
    viewModel: RecipeDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var showDeleteDialog by remember { mutableStateOf(false) }
    var showMoreMenu by remember { mutableStateOf(false) }

    LaunchedEffect(recipeId) { viewModel.load(recipeId) }

    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { showDeleteDialog = false },
            title = { Text("Delete recipe") },
            text = { Text("Delete \"${state.recipe?.name}\"? This cannot be undone.") },
            confirmButton = {
                TextButton(onClick = { showDeleteDialog = false; viewModel.deleteRecipe(onBack) }) {
                    Text("Delete", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = { TextButton(onClick = { showDeleteDialog = false }) { Text("Cancel") } },
        )
    }

    DisposableEffect(state.keepScreenOn) {
        val window = (context as? Activity)?.window
        if (state.keepScreenOn) {
            window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
        onDispose {
            window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(state.recipe?.name ?: "Recipe", maxLines = 1) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "Back") }
                },
                actions = {
                    IconButton(onClick = viewModel::toggleKeepScreenOn) {
                        Icon(
                            if (state.keepScreenOn) Icons.Default.LightMode else Icons.Default.Bedtime,
                            contentDescription = "Keep screen on",
                            tint = if (state.keepScreenOn) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                        )
                    }
                    IconButton(onClick = viewModel::toggleMetric) {
                        Icon(
                            Icons.Default.Straighten,
                            contentDescription = "Convert units",
                            tint = if (state.metricMode) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                        )
                    }
                    IconButton(onClick = onEdit) { Icon(Icons.Default.Edit, "Edit") }
                    Box {
                        IconButton(onClick = { showMoreMenu = true }) {
                            Icon(Icons.Default.MoreVert, "More")
                        }
                        DropdownMenu(expanded = showMoreMenu, onDismissRequest = { showMoreMenu = false }) {
                            DropdownMenuItem(
                                text = { Text("Delete recipe", color = MaterialTheme.colorScheme.error) },
                                leadingIcon = { Icon(Icons.Default.Delete, null, tint = MaterialTheme.colorScheme.error) },
                                onClick = { showMoreMenu = false; showDeleteDialog = true },
                            )
                        }
                    }
                },
            )
        },
    ) { padding ->
        when {
            state.isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            state.error != null -> Box(Modifier.fillMaxSize().padding(16.dp), contentAlignment = Alignment.Center) {
                Text(state.error!!, color = MaterialTheme.colorScheme.error)
            }
            state.recipe != null -> RecipeContent(
                recipe = state.recipe!!,
                servings = state.servings,
                originalServings = state.originalServings,
                ingredients = viewModel.getDisplayIngredients(),
                instructions = viewModel.getDisplayInstructions(),
                metricMode = state.metricMode,
                onServingsChange = viewModel::setServings,
                modifier = Modifier.padding(padding),
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun RecipeContent(
    recipe: Recipe,
    servings: Int,
    originalServings: Int,
    ingredients: List<String>,
    instructions: List<String>,
    metricMode: Boolean,
    onServingsChange: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val uriHandler = LocalUriHandler.current

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp),
    ) {
        // Hero image
        item {
            AsyncImage(
                model = recipe.image.ifBlank { null },
                contentDescription = recipe.name,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxWidth().height(220.dp),
            )
        }

        // Title + keywords
        item {
            Column(Modifier.padding(16.dp)) {
                Text(recipe.name, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                if (recipe.keywords.isNotBlank()) {
                    Spacer(Modifier.height(8.dp))
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        recipe.keywords.split(",").map { it.trim() }.filter { it.isNotBlank() }.forEach { kw ->
                            SuggestionChip(onClick = {}, label = { Text(kw, style = MaterialTheme.typography.labelSmall) })
                        }
                    }
                }
            }
        }

        // Meta info card
        item {
            val prep = parseDurationMinutes(recipe.prepTime)
            val cook = parseDurationMinutes(recipe.cookTime)
            val total = parseDurationMinutes(recipe.totalTime)
            val metaItems = buildList {
                if (prep > 0) add("Prep" to formatMinutes(prep))
                if (cook > 0) add("Cook" to formatMinutes(cook))
                if (total > 0) add("Total" to formatMinutes(total))
                if (recipe.recipeCategory.isNotBlank()) add("Category" to recipe.recipeCategory)
            }
            if (metaItems.isNotEmpty() || recipe.url.isNotBlank()) {
                ElevatedCard(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        metaItems.forEach { (k, v) ->
                            Row {
                                Text(k, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, modifier = Modifier.width(80.dp))
                                Text(v, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                        if (recipe.url.isNotBlank()) {
                            Row {
                                Text("Source", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, modifier = Modifier.width(80.dp))
                                TextButton(
                                    onClick = { runCatching { uriHandler.openUri(recipe.url) } },
                                    contentPadding = PaddingValues(0.dp),
                                ) {
                                    Text(
                                        runCatching { java.net.URI(recipe.url).host ?: recipe.url }.getOrDefault(recipe.url),
                                        style = MaterialTheme.typography.bodySmall,
                                        maxLines = 1,
                                    )
                                }
                            }
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
            }
        }

        // Description
        if (recipe.description.isNotBlank()) {
            item {
                Text(recipe.description, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(horizontal = 16.dp))
                Spacer(Modifier.height(12.dp))
            }
        }

        // Servings + metric toggle
        item {
            Row(
                Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Servings:", style = MaterialTheme.typography.labelLarge)
                IconButton(onClick = { onServingsChange(servings - 1) }, enabled = servings > 1) {
                    Icon(Icons.Default.Remove, "Less")
                }
                Text("$servings", style = MaterialTheme.typography.titleMedium)
                IconButton(onClick = { onServingsChange(servings + 1) }) {
                    Icon(Icons.Default.Add, "More")
                }
                Spacer(Modifier.weight(1f))
                FilterChip(
                    selected = metricMode,
                    onClick = {},
                    label = { Text("Metric") },
                    leadingIcon = if (metricMode) ({ Icon(Icons.Default.Check, null, Modifier.size(16.dp)) }) else null,
                )
            }
            HorizontalDivider(Modifier.padding(horizontal = 16.dp, vertical = 4.dp))
        }

        // Ingredients
        if (ingredients.isNotEmpty()) {
            item {
                Text("Ingredients", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
            }
            items(ingredients) { ing ->
                Row(Modifier.padding(horizontal = 24.dp, vertical = 2.dp)) {
                    Text("•", Modifier.width(16.dp))
                    Text(ing, style = MaterialTheme.typography.bodyMedium)
                }
            }
            item { Spacer(Modifier.height(12.dp)) }
        }

        // Instructions
        if (instructions.isNotEmpty()) {
            item {
                HorizontalDivider(Modifier.padding(horizontal = 16.dp, vertical = 4.dp))
                Text("Instructions", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
            }
            itemsIndexed(instructions) { index, step ->
                Row(
                    Modifier.padding(horizontal = 16.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Surface(
                        shape = MaterialTheme.shapes.small,
                        color = MaterialTheme.colorScheme.primaryContainer,
                        modifier = Modifier.size(28.dp),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(
                                "${index + 1}",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                                fontWeight = FontWeight.Bold,
                            )
                        }
                    }
                    Text(step, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                }
            }
            item { Spacer(Modifier.height(12.dp)) }
        }

        // Tools
        if (recipe.tools.isNotEmpty()) {
            item {
                HorizontalDivider(Modifier.padding(horizontal = 16.dp, vertical = 4.dp))
                Text("Tools", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
            }
            items(recipe.tools) { tool ->
                Row(Modifier.padding(horizontal = 24.dp, vertical = 2.dp)) {
                    Text("•", Modifier.width(16.dp))
                    Text(tool, style = MaterialTheme.typography.bodyMedium)
                }
            }
            item { Spacer(Modifier.height(12.dp)) }
        }

        // Nutrition
        recipe.nutrition?.let { n ->
            val fields = buildList {
                if (n.calories.isNotBlank()) add("Energy" to n.calories)
                if (n.carbohydrateContent.isNotBlank()) add("Carbs" to n.carbohydrateContent)
                if (n.sugarContent.isNotBlank()) add("Sugar" to n.sugarContent)
                if (n.fatContent.isNotBlank()) add("Fat" to n.fatContent)
                if (n.saturatedFatContent.isNotBlank()) add("Sat. fat" to n.saturatedFatContent)
                if (n.fiberContent.isNotBlank()) add("Fibre" to n.fiberContent)
                if (n.proteinContent.isNotBlank()) add("Protein" to n.proteinContent)
                if (n.sodiumContent.isNotBlank()) add("Sodium" to n.sodiumContent)
                if (n.servingSize.isNotBlank()) add("Serving" to n.servingSize)
            }
            if (fields.isNotEmpty()) {
                item {
                    HorizontalDivider(Modifier.padding(horizontal = 16.dp, vertical = 4.dp))
                    Text("Nutrition", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
                    ElevatedCard(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            fields.chunked(3).forEach { row ->
                                Row(Modifier.fillMaxWidth()) {
                                    row.forEach { (k, v) ->
                                        Column(Modifier.weight(1f)) {
                                            Text(k, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                                            Text(v, style = MaterialTheme.typography.bodySmall)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                }
            }
        }
    }
}
