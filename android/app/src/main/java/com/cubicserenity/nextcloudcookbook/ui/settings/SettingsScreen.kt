package com.cubicserenity.nextcloudcookbook.ui.settings

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    viewModel: SettingsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showPassword by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "Back") }
                },
                actions = {
                    TextButton(onClick = { viewModel.save(); onBack() }) {
                        Text("Save")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("Server", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)

            OutlinedTextField(
                value = state.serverUrl,
                onValueChange = { viewModel.update { copy(serverUrl = it) } },
                label = { Text("Server URL") },
                placeholder = { Text("https://cloud.example.com") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                leadingIcon = { Icon(Icons.Default.Cloud, null) },
            )

            OutlinedTextField(
                value = state.username,
                onValueChange = { viewModel.update { copy(username = it) } },
                label = { Text("Username") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                leadingIcon = { Icon(Icons.Default.Person, null) },
            )

            OutlinedTextField(
                value = state.password,
                onValueChange = { viewModel.update { copy(password = it) } },
                label = { Text("Password") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                visualTransformation = if (showPassword) VisualTransformation.None else PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                leadingIcon = { Icon(Icons.Default.Lock, null) },
                trailingIcon = {
                    IconButton(onClick = { showPassword = !showPassword }) {
                        Icon(if (showPassword) Icons.Default.VisibilityOff else Icons.Default.Visibility, "Toggle password")
                    }
                },
            )

            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = state.ignoreSsl,
                    onCheckedChange = { viewModel.update { copy(ignoreSsl = it) } },
                )
                Spacer(Modifier.width(8.dp))
                Column {
                    Text("Trust all certificates", style = MaterialTheme.typography.bodyMedium)
                    Text("Enable for self-signed certificates", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = viewModel::testConnection,
                    enabled = !state.isTesting,
                    modifier = Modifier.weight(1f),
                ) {
                    if (state.isTesting) {
                        CircularProgressIndicator(Modifier.size(16.dp))
                    } else {
                        Icon(Icons.Default.NetworkCheck, null, Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Test Connection")
                    }
                }
                Button(
                    onClick = { viewModel.save(); onBack() },
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(Icons.Default.Save, null, Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Save")
                }
            }

            state.testResult?.let { result ->
                val isSuccess = result.startsWith("Connection successful")
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = if (isSuccess) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer,
                    ),
                ) {
                    Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Icon(
                            if (isSuccess) Icons.Default.CheckCircle else Icons.Default.Error,
                            null,
                            tint = if (isSuccess) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onErrorContainer,
                        )
                        Text(result, style = MaterialTheme.typography.bodySmall, color = if (isSuccess) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onErrorContainer)
                    }
                }
            }

            if (state.isSaved) {
                Text("Settings saved.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
            }

            HorizontalDivider()
            Text("About", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
            Text("Nextcloud Cookbook v1.0.0\nRequires Nextcloud with the Cookbook app installed.", style = MaterialTheme.typography.bodySmall)
        }
    }
}
