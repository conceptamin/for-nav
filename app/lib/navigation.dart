// WebView 안의 이동을 어디서 열지 정한다(app-front/README.md "외부 링크와 전화"의 두 번째 겹).
// 웹이 init 뒤에 openExternal로 넘기는 것이 첫 겹이고, 여기는 그 전의 이동이나 window.location 변경이
// WebView 안에서 다른 사이트를 열지 않게 막는다.

enum NavigationTarget {
  /// 앱 출처 안. WebView에서 연다
  app,

  /// 앱 출처 밖(tel:·mailto:·sms:·다른 사이트). 막고 외부 앱으로 연다
  external,

  /// 앱 출처 밖의 하위 프레임. 막기만 한다(사용자가 누른 이동이 아니다)
  blocked,
}

NavigationTarget classifyNavigation(String url, Uri appUri, {required bool isMainFrame}) {
  final uri = Uri.tryParse(url);
  if (uri == null) return NavigationTarget.blocked;
  if (uri.scheme == 'about') return NavigationTarget.app;
  if (isSameOrigin(uri, appUri)) return NavigationTarget.app;
  return isMainFrame ? NavigationTarget.external : NavigationTarget.blocked;
}

/// Uri.origin은 http(s)가 아니면 예외를 던지므로 scheme부터 본다
bool isSameOrigin(Uri uri, Uri appUri) {
  if (uri.scheme != 'http' && uri.scheme != 'https') return false;
  return uri.origin == appUri.origin;
}
