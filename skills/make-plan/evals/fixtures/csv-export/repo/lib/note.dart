class Note {
  const Note({
    required this.title,
    required this.body,
    required this.createdAt,
  });

  final String title;
  final String body;
  final DateTime createdAt;
}
