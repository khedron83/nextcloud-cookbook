package com.cubicserenity.nextcloudcookbook.ui.recipes

import androidx.compose.animation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.cubicserenity.nextcloudcookbook.ui.home.OfflineBanner
import com.cubicserenity.nextcloudcookbook.ui.home.RecipeCard

@OptIn(ExperimentalMaterial3Api::class, ExperimentalAnimationApi::class)
@Composable
fun RecipesScreen(
    onRecipeClick: (Int) -> Unit,
    onNewRecipe: () -> Unit,
    onImportUrl: () -> Unit,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: RecipesViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var searchActive by remember { mutableStateOf(false) }
    var showMoreMenu by remember { mutableStateOf(false) }
    var showAddDialog by remember { mutableStateOf(false) }
    val focusRequester = remember { FocusRequester() }
    val keyboard = LocalSoftwareKeyboardController.current

    LaunchedEffect(searchActive) {
        if (searchActive) focusRequester.requestFocus()
    }

    if (showAddDialog) {
        AlertDialog(
            onDismissRequest = { showAddDialog = false },
            title = { Text("Add Recipe") },
            text = { Text("How would you like to add a recipe?") },
            confirmButton = {
                TextButton(onClick = { showAddDialog = false; onImportUrl() }) {
                    Icon(Icons.Default.Link, null, Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Import from URL")
                }
            },
            dismissButton = {
                TextButton(onClick = { showAddDialog = false; onNewRecipe() }) {
                    Icon(Icons.Default.Edit, null, Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Enter manually")
                }
            },
        )
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = {
                    AnimatedContent(targetState = searchActive, label = "search") { active ->
                        if (active) {
                            OutlinedTextField(
                                value = state.query,
                                onValueChange = viewModel::setQuery,
                                placeholder = { Text("Search recipes…") },
                                modifier = Modifier.fillMaxWidth().focusRequester(focusRequester),
                                singleLine = true,
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = MaterialTheme.colorScheme.primary,
                                ),
                                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                                keyboardActions = KeyboardActions(onSearch = { keyboard?.hide() }),
                            )
                        } else {
                            Text("Nextcloud Cookbook")
                        }
                    }
                },
                actions = {
                    if (searchActive) {
                        IconButton(onClick = { viewModel.setQuery(""); searchActive = false; keyboard?.hide() }) {
                            Icon(Icons.Default.Close, "Close search")
                        }
                    } else {
                        IconButton(onClick = { searchActive = true }) {
                            Icon(Icons.Default.Search, "Search")
                        }
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
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddDialog = true }) {
                Icon(Icons.Default.Add, "Add Recipe")
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            if (state.isUnconfigured) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        Icon(Icons.Default.Cloud, null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.secondary)
                        Text("No server configured", style = MaterialTheme.typography.titleMedium)
                        Text("Add your Nextcloud details to get started.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.secondary)
                        Button(onClick = onOpenSettings) {
                            Icon(Icons.Default.Settings, null, Modifier.size(18.dp))
                            Spacer(Modifier.width(8.dp))
                            Text("Open Settings")
                        }
                    }
                }
                return@Column
            }
            if (state.isOffline) {
                OfflineBanner(error = state.error, onRetry = viewModel::refresh)
            }
            val displayed = state.filtered
            when {
                state.isLoading && displayed.isEmpty() -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
                displayed.isEmpty() && state.query.isNotBlank() -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("No results for \"${state.query}\"")
                    }
                }
                displayed.isEmpty() -> {
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
                        items(displayed, key = { it.id }) { recipe ->
                            RecipeCard(recipe, state.serverUrl, onRecipeClick)
                        }
                    }
                }
            }
        }
    }
}
