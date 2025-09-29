import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';
import '../widgets/loading_indicator.dart';

class RepositoryScreen extends StatefulWidget {
  @override
  _RepositoryScreenState createState() => _RepositoryScreenState();
}

class _RepositoryScreenState extends State<RepositoryScreen> {
  final TextEditingController _repoController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _repoController.dispose();
    super.dispose();
  }

  bool _isValidGitHubUrl(String url) {
    final regex = RegExp(r'^https?://github\.com/[^/]+/[^/]+/?$');
    return regex.hasMatch(url);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Repository'),
        actions: [
          Consumer<ChatProvider>(
            builder: (context, provider, child) {
              if (provider.isRepositoryLoaded) {
                return PopupMenuButton(
                  itemBuilder: (context) => [
                    PopupMenuItem(
                      value: 'clear',
                      child: Text('Clear Repository'),
                    ),
                  ],
                  onSelected: (value) {
                    if (value == 'clear') {
                      provider.clearRepository();
                    }
                  },
                );
              }
              return SizedBox.shrink();
            },
          ),
        ],
      ),
      body: Consumer<ChatProvider>(
        builder: (context, provider, child) {
          return Padding(
            padding: EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Current repository status
                if (provider.isRepositoryLoaded)
                  Card(
                    color: Colors.green[50],
                    child: Padding(
                      padding: EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Repository Loaded',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.green[700],
                              fontSize: 16,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            provider.currentRepository ?? '',
                            style: TextStyle(color: Colors.green[600]),
                          ),
                        ],
                      ),
                    ),
                  ),

                SizedBox(height: 20),

                // Repository input form
                Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Enter GitHub Repository URL',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      SizedBox(height: 16),
                      TextFormField(
                        controller: _repoController,
                        decoration: InputDecoration(
                          labelText: 'GitHub Repository URL',
                          hintText: 'https://github.com/username/repository',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.link),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter a repository URL';
                          }
                          if (!_isValidGitHubUrl(value)) {
                            return 'Please enter a valid GitHub URL';
                          }
                          return null;
                        },
                      ),
                      SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: provider.isLoading
                            ? null
                            : () {
                                if (_formKey.currentState!.validate()) {
                                  provider.ingestRepository(_repoController.text.trim());
                                }
                              },
                        child: provider.isLoading
                            ? Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  ),
                                  SizedBox(width: 10),
                                  Text('Ingesting Repository...'),
                                ],
                              )
                            : Text('Ingest Repository'),
                        style: ElevatedButton.styleFrom(
                          padding: EdgeInsets.all(16),
                        ),
                      ),
                    ],
                  ),
                ),

                SizedBox(height: 20),

                // Error display
                if (provider.error != null)
                  Card(
                    color: Colors.red[50],
                    child: Padding(
                      padding: EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Error',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.red[700],
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            provider.error!,
                            style: TextStyle(color: Colors.red[600]),
                          ),
                        ],
                      ),
                    ),
                  ),

                Spacer(),

                // Instructions
                Card(
                  color: Colors.blue[50],
                  child: Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Instructions',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.blue[700],
                          ),
                        ),
                        SizedBox(height: 8),
                        Text(
                          '1. Enter a valid GitHub repository URL\n'
                          '2. Click "Ingest Repository" to process the code\n'
                          '3. Once loaded, go to Chat tab to ask questions',
                          style: TextStyle(color: Colors.blue[600]),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}