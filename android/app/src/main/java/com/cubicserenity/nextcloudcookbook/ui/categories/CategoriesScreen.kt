package com.cubicserenity.nextcloudcookbook.ui.categories

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.cubicserenity.nextcloudcookbook.ui.home.RecipeCard
import com.cubicserenity.nextcloudcookbook.ui.home.RenameCategoryDialog

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CategoriesScreen(
    onRecipeClick: (Int) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: CategoriesViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var renameTarget by remember { mutableStateOf<String?>(null) }

    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = {
                    if (state.selectedCategory != null)
                        Text(state.selectedCategory!!, maxLines = 1)
                    else
                        Text("Categories")
                },
                navigationIcon = {
                    if (state.selectedCategory != null) {
                        IconButton(onClick = { viewModel.selectCategory(null) }) {
                            Icon(Icons.Default.ArrowBack, "Back")
                        }
                    }
                },
                actions = {
                    if (state.selectedCategory == null) {
                        IconButton(onClick = viewModel::loadCategories) {
                            Icon(Icons.Default.Refresh, "Refresh")
                        }
                    } else {
                        IconButton(onClick = { renameTarget = state.selectedCategory }) {
                            Icon(Icons.Default.Edit, "Rename")
                        }
                    }
                },
            )
        },
    ) { padding ->
        if (state.selectedCategory == null) {
            // Category list
            if (state.categories.isEmpty()) {
                Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                    Text("No categories yet")
                }
            } else {
                LazyColumn(
                    Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(8.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    items(state.categories, key = { it.first }) { (name, count) ->
                        CategoryCard(name = name, count = count, onClick = { viewModel.selectCategory(name) })
                    }
                }
            }
        } else {
            // Recipes in category
            if (state.isLoading) {
                Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(160.dp),
                    contentPadding = PaddingValues(8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxSize().padding(padding),
                ) {
                    items(state.categoryRecipes, key = { it.id }) { recipe ->
                        RecipeCard(recipe, state.serverUrl, onRecipeClick)
                    }
                }
            }
        }
    }

    renameTarget?.let { target ->
        RenameCategoryDialog(
            current = target,
            onConfirm = { newName ->
                viewModel.renameCategory(target, newName)
                viewModel.selectCategory(null)
                renameTarget = null
            },
            onDismiss = { renameTarget = null },
        )
    }
}

@Composable
private fun CategoryCard(name: String, count: Int, onClick: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Row(
            Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Icon(Icons.Default.FolderOpen, null, tint = MaterialTheme.colorScheme.primary)
            Text(name, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
            Text(
                "$count",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.secondary,
            )
            Icon(Icons.Default.ChevronRight, null, tint = MaterialTheme.colorScheme.secondary)
        }
    }
}
