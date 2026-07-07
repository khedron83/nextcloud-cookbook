package com.cubicserenity.nextcloudcookbook.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil3.compose.AsyncImage
import com.cubicserenity.nextcloudcookbook.domain.model.RecipeSummary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onRecipeClick: (Int) -> Unit,
    onNewRecipe: () -> Unit,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    var showMoreMenu by remember { mutableStateOf(false) }
    var renameCategoryTarget by remember { mutableStateOf<String?>(null) }

    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = { Text("Nextcloud Cookbook") },
                actions = {
                    IconButton(onClick = { viewModel.refresh() }) {
                        Icon(Icons.Default.Refresh, "Refresh")
                    }
                    Box {
                        IconButton(onClick = { showMoreMenu = true }) {
                            Icon(Icons.Default.MoreVert, "More")
                        }
                        DropdownMenu(expanded = showMoreMenu, onDismissRequest = { showMoreMenu = false }) {
                            DropdownMenuItem(
                                text = { Text("Reindex") },
                                leadingIcon = { Icon(Icons.Default.Sync, null) },
                                onClick = { showMoreMenu = false; viewModel.reindex() },
                            )
                            DropdownMenuItem(
                                text = { Text("Settings") },
                                leadingIcon = { Icon(Icons.Default.Settings, null) },
                                onClick = { showMoreMenu = false; onOpenSettings() },
                            )
                        }
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = onNewRecipe) {
                Icon(Icons.Default.Add, "New Recipe")
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            if (state.isOffline) {
                OfflineBanner(
                    error = state.error,
                    onRetry = { viewModel.refresh() },
                )
            }
            when {
                state.isLoading && state.allRecipes.isEmpty() -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
                state.allRecipes.isEmpty() -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("No recipes yet. Tap + to add one.")
                    }
                }
                else -> {
                    LazyVerticalGrid(
                        columns = GridCells.Adaptive(160.dp),
                        contentPadding = PaddingValues(8.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxSize(),
                    ) {
                        items(state.allRecipes, key = { it.id }) { recipe ->
                            RecipeCard(recipe, state.serverUrl, onRecipeClick)
                        }
                    }
                }
            }
        }
    }

    renameCategoryTarget?.let { target ->
        RenameCategoryDialog(
            current = target,
            onConfirm = { newName -> viewModel.renameCategory(target, newName); renameCategoryTarget = null },
            onDismiss = { renameCategoryTarget = null },
        )
    }
}

@Composable
fun RecipeCard(
    recipe: RecipeSummary,
    serverUrl: String,
    onClick: (Int) -> Unit,
) {
    val imageUrl = serverUrl.trimEnd('/').takeIf { it.isNotBlank() }
        ?.let { "$it/index.php/apps/cookbook/api/v1/recipes/${recipe.id}/image?size=thumb" }

    Card(onClick = { onClick(recipe.id) }, modifier = Modifier.fillMaxWidth()) {
        Column {
            AsyncImage(
                model = imageUrl,
                contentDescription = recipe.name,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxWidth().height(120.dp).clip(MaterialTheme.shapes.medium),
            )
            Column(Modifier.padding(8.dp)) {
                Text(recipe.name, style = MaterialTheme.typography.titleSmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
                if (recipe.category.isNotBlank()) {
                    Text(recipe.category, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.secondary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }
        }
    }
}

@Composable
fun OfflineBanner(error: String?, onRetry: () -> Unit) {
    Surface(color = MaterialTheme.colorScheme.errorContainer) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.WifiOff, null, tint = MaterialTheme.colorScheme.onErrorContainer)
            Spacer(Modifier.width(8.dp))
            Text(
                error ?: "Offline — showing cached data",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onErrorContainer,
                modifier = Modifier.weight(1f),
            )
            TextButton(onClick = onRetry) { Text("Retry", color = MaterialTheme.colorScheme.onErrorContainer) }
        }
    }
}

@Composable
fun RenameCategoryDialog(current: String, onConfirm: (String) -> Unit, onDismiss: () -> Unit) {
    var text by remember { mutableStateOf(current) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Rename Category") },
        text = { OutlinedTextField(value = text, onValueChange = { text = it }, label = { Text("Name") }, singleLine = true) },
        confirmButton = { TextButton(onClick = { if (text.isNotBlank() && text != current) onConfirm(text) }, enabled = text.isNotBlank() && text != current) { Text("Rename") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
