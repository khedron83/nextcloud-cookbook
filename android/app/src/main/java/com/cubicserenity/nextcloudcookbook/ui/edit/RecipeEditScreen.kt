package com.cubicserenity.nextcloudcookbook.ui.edit

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RecipeEditScreen(
    recipeId: Int?,
    onSaved: (Int) -> Unit,
    onCancel: () -> Unit,
    openImportDialog: Boolean = false,
    viewModel: RecipeEditViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showImportDialog by remember { mutableStateOf(openImportDialog) }
    var importUrl by remember { mutableStateOf("") }

    LaunchedEffect(recipeId) { viewModel.load(recipeId) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (recipeId == null) "New Recipe" else "Edit Recipe") },
                navigationIcon = {
                    IconButton(onClick = onCancel) { Icon(Icons.Default.Close, "Cancel") }
                },
                actions = {
                    if (recipeId == null) {
                        IconButton(onClick = { showImportDialog = true }) {
                            Icon(Icons.Default.Link, "Import from URL")
                        }
                    }
                    IconButton(onClick = { viewModel.save(onSaved) }, enabled = !state.isSaving) {
                        if (state.isSaving) CircularProgressIndicator(Modifier.size(20.dp))
                        else Icon(Icons.Default.Save, "Save")
                    }
                },
            )
        },
    ) { padding ->
        if (state.isLoading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            return@Scaffold
        }

        LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item { SectionHeader("Basic Info") }

            item {
                OutlinedTextField(
                    value = state.name,
                    onValueChange = { viewModel.update { copy(name = it) } },
                    label = { Text("Recipe Name *") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    isError = state.error == "Name is required",
                )
            }
            item {
                OutlinedTextField(
                    value = state.description,
                    onValueChange = { viewModel.update { copy(description = it) } },
                    label = { Text("Description") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 2, maxLines = 4,
                )
            }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = state.url,
                        onValueChange = { viewModel.update { copy(url = it) } },
                        label = { Text("Source URL") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                    )
                    OutlinedTextField(
                        value = state.recipeYield,
                        onValueChange = { viewModel.update { copy(recipeYield = it) } },
                        label = { Text("Yield") },
                        modifier = Modifier.width(100.dp),
                        singleLine = true,
                    )
                }
            }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = state.category,
                        onValueChange = { viewModel.update { copy(category = it) } },
                        label = { Text("Category") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                    )
                    OutlinedTextField(
                        value = state.keywords,
                        onValueChange = { viewModel.update { copy(keywords = it) } },
                        label = { Text("Keywords (comma-sep)") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                    )
                }
            }

            item { SectionHeader("Timings (minutes)") }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    MinuteField("Prep", state.prepTimeMin, { viewModel.update { copy(prepTimeMin = it) } }, Modifier.weight(1f))
                    MinuteField("Cook", state.cookTimeMin, { viewModel.update { copy(cookTimeMin = it) } }, Modifier.weight(1f))
                    MinuteField("Total", state.totalTimeMin, { viewModel.update { copy(totalTimeMin = it) } }, Modifier.weight(1f))
                }
            }

            item {
                HorizontalDivider()
                SectionHeader("Ingredients")
            }
            itemsIndexed(state.ingredients) { i, ing ->
                EditableListItem(
                    value = ing,
                    onValueChange = { viewModel.updateIngredient(i, it) },
                    onDelete = { viewModel.removeIngredient(i) },
                    placeholder = "e.g. 200g flour",
                )
            }
            item {
                TextButton(onClick = viewModel::addIngredient, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.Add, null)
                    Spacer(Modifier.width(4.dp))
                    Text("Add Ingredient")
                }
            }

            item {
                HorizontalDivider()
                SectionHeader("Instructions")
            }
            itemsIndexed(state.instructions) { i, step ->
                EditableListItem(
                    value = step,
                    onValueChange = { viewModel.updateInstruction(i, it) },
                    onDelete = { viewModel.removeInstruction(i) },
                    placeholder = "Step ${i + 1}",
                    label = "${i + 1}.",
                    minLines = 2,
                )
            }
            item {
                TextButton(onClick = viewModel::addInstruction, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.Add, null)
                    Spacer(Modifier.width(4.dp))
                    Text("Add Step")
                }
            }

            item {
                HorizontalDivider()
                SectionHeader("Tools (optional)")
            }
            itemsIndexed(state.tools) { i, tool ->
                EditableListItem(
                    value = tool,
                    onValueChange = { viewModel.updateTool(i, it) },
                    onDelete = { viewModel.removeTool(i) },
                    placeholder = "e.g. Stand mixer",
                )
            }
            item {
                TextButton(onClick = viewModel::addTool, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.Add, null)
                    Spacer(Modifier.width(4.dp))
                    Text("Add Tool")
                }
            }

            item {
                HorizontalDivider()
                SectionHeader("Nutrition (optional)")
            }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    val n = state.nutrition
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        NutrField("Calories", n.calories, { viewModel.update { copy(nutrition = nutrition.copy(calories = it)) } }, Modifier.weight(1f))
                        NutrField("Protein", n.proteinContent, { viewModel.update { copy(nutrition = nutrition.copy(proteinContent = it)) } }, Modifier.weight(1f))
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        NutrField("Carbs", n.carbohydrateContent, { viewModel.update { copy(nutrition = nutrition.copy(carbohydrateContent = it)) } }, Modifier.weight(1f))
                        NutrField("Sugar", n.sugarContent, { viewModel.update { copy(nutrition = nutrition.copy(sugarContent = it)) } }, Modifier.weight(1f))
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        NutrField("Fat", n.fatContent, { viewModel.update { copy(nutrition = nutrition.copy(fatContent = it)) } }, Modifier.weight(1f))
                        NutrField("Sat. fat", n.saturatedFatContent, { viewModel.update { copy(nutrition = nutrition.copy(saturatedFatContent = it)) } }, Modifier.weight(1f))
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        NutrField("Fibre", n.fiberContent, { viewModel.update { copy(nutrition = nutrition.copy(fiberContent = it)) } }, Modifier.weight(1f))
                        NutrField("Sodium", n.sodiumContent, { viewModel.update { copy(nutrition = nutrition.copy(sodiumContent = it)) } }, Modifier.weight(1f))
                    }
                    NutrField("Serving size", n.servingSize, { viewModel.update { copy(nutrition = nutrition.copy(servingSize = it)) } }, Modifier.fillMaxWidth())
                }
            }

            state.error?.let { err ->
                item {
                    if (err != "Name is required") {
                        Text(err, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }

    if (showImportDialog) {
        AlertDialog(
            onDismissRequest = { showImportDialog = false },
            title = { Text("Import Recipe from URL") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (state.isImporting) CircularProgressIndicator()
                    else OutlinedTextField(
                        value = importUrl,
                        onValueChange = { importUrl = it },
                        label = { Text("Recipe URL") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = { viewModel.importFromUrl(importUrl) { showImportDialog = false } },
                    enabled = importUrl.isNotBlank() && !state.isImporting,
                ) { Text("Import") }
            },
            dismissButton = {
                TextButton(onClick = { showImportDialog = false }) { Text("Cancel") }
            },
        )
    }
}

@Composable
private fun SectionHeader(title: String) {
    Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 4.dp, bottom = 2.dp))
}

@Composable
private fun MinuteField(label: String, value: Int, onChange: (Int) -> Unit, modifier: Modifier = Modifier) {
    OutlinedTextField(
        value = if (value == 0) "" else value.toString(),
        onValueChange = { onChange(it.toIntOrNull() ?: 0) },
        label = { Text(label) },
        modifier = modifier,
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
    )
}

@Composable
private fun NutrField(label: String, value: String, onChange: (String) -> Unit, modifier: Modifier = Modifier) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        modifier = modifier,
        singleLine = true,
    )
}

@Composable
private fun EditableListItem(
    value: String,
    onValueChange: (String) -> Unit,
    onDelete: () -> Unit,
    placeholder: String = "",
    label: String? = null,
    minLines: Int = 1,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        if (label != null) {
            Text(label, style = MaterialTheme.typography.labelMedium, modifier = Modifier.width(24.dp))
        }
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            placeholder = { Text(placeholder, style = MaterialTheme.typography.bodySmall) },
            modifier = Modifier.weight(1f),
            minLines = minLines,
            maxLines = minLines + 2,
        )
        IconButton(onClick = onDelete) {
            Icon(Icons.Default.Delete, "Remove", tint = MaterialTheme.colorScheme.error)
        }
    }
}
