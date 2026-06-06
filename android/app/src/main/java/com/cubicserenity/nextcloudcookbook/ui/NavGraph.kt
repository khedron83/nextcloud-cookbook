package com.cubicserenity.nextcloudcookbook.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.cubicserenity.nextcloudcookbook.ui.categories.CategoriesScreen
import com.cubicserenity.nextcloudcookbook.ui.detail.RecipeDetailScreen
import com.cubicserenity.nextcloudcookbook.ui.edit.RecipeEditScreen
import com.cubicserenity.nextcloudcookbook.ui.mealplanner.MealPlannerScreen
import com.cubicserenity.nextcloudcookbook.ui.recipes.RecipesScreen
import com.cubicserenity.nextcloudcookbook.ui.settings.SettingsScreen
import com.cubicserenity.nextcloudcookbook.ui.shopping.ShoppingScreen

private enum class Tab(val label: String, val icon: ImageVector) {
    RECIPES("Recipes", Icons.Default.MenuBook),
    CATEGORIES("Categories", Icons.Default.FolderOpen),
    PLANNER("Planner", Icons.Default.CalendarMonth),
    SHOPPING("Shopping", Icons.Default.ShoppingCart),
}

@Composable
fun NavGraph() {
    val rootNav = rememberNavController()
    NavHost(rootNav, startDestination = "main") {
        composable("main") {
            MainShell(
                onRecipeClick = { rootNav.navigate("detail/$it") },
                onNewRecipe = { rootNav.navigate("edit?id=-1&import=false") },
                onImportUrl = { rootNav.navigate("edit?id=-1&import=true") },
                onOpenSettings = { rootNav.navigate("settings") },
            )
        }
        composable(
            "detail/{id}",
            arguments = listOf(navArgument("id") { type = NavType.IntType }),
        ) { back ->
            val id = back.arguments!!.getInt("id")
            RecipeDetailScreen(
                recipeId = id,
                onBack = { rootNav.popBackStack() },
                onEdit = { rootNav.navigate("edit?id=$id&import=false") },
            )
        }
        composable(
            "edit?id={id}&import={import}",
            arguments = listOf(
                navArgument("id") { type = NavType.IntType; defaultValue = -1 },
                navArgument("import") { type = NavType.BoolType; defaultValue = false },
            ),
        ) { back ->
            val id = back.arguments!!.getInt("id").takeIf { it != -1 }
            val openImport = back.arguments!!.getBoolean("import")
            RecipeEditScreen(
                recipeId = id,
                openImportDialog = openImport,
                onSaved = { savedId ->
                    rootNav.popBackStack()
                    rootNav.navigate("detail/$savedId")
                },
                onCancel = { rootNav.popBackStack() },
            )
        }
        composable("settings") {
            SettingsScreen(onBack = { rootNav.popBackStack() })
        }
    }
}

@Composable
private fun MainShell(
    onRecipeClick: (Int) -> Unit,
    onNewRecipe: () -> Unit,
    onImportUrl: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    var selectedTab by rememberSaveable { mutableStateOf(Tab.RECIPES) }

    Scaffold(
        bottomBar = {
            NavigationBar {
                Tab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = selectedTab == tab,
                        onClick = { selectedTab = tab },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { padding ->
        when (selectedTab) {
            Tab.RECIPES -> RecipesScreen(
                modifier = Modifier.padding(padding),
                onRecipeClick = onRecipeClick,
                onNewRecipe = onNewRecipe,
                onImportUrl = onImportUrl,
                onOpenSettings = onOpenSettings,
            )
            Tab.CATEGORIES -> CategoriesScreen(
                modifier = Modifier.padding(padding),
                onRecipeClick = onRecipeClick,
            )
            Tab.PLANNER -> MealPlannerScreen(
                modifier = Modifier.padding(padding),
            )
            Tab.SHOPPING -> ShoppingScreen(
                modifier = Modifier.padding(padding),
            )
        }
    }
}
