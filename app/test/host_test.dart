import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:for_nav/bridge.dart';
import 'package:for_nav/navigation.dart';

void main() {
  final app = Uri.parse('http://10.0.2.2:5181');

  group('classifyNavigation', () {
    NavigationTarget main(String url) => classifyNavigation(url, app, isMainFrame: true);

    test('앱 출처 안은 WebView에서 연다', () {
      expect(main('http://10.0.2.2:5181/__host'), NavigationTarget.app);
      expect(main('about:blank'), NavigationTarget.app);
    });

    test('전화·문자·메일과 다른 사이트는 외부로 연다', () {
      expect(main('tel:119'), NavigationTarget.external);
      expect(main('sms:01000000000'), NavigationTarget.external);
      expect(main('mailto:a@example.com'), NavigationTarget.external);
      expect(main('https://map.kakao.com/link/search/울산'), NavigationTarget.external);
      // 포트·scheme이 다르면 다른 출처다
      expect(main('http://10.0.2.2:8000/api'), NavigationTarget.external);
      expect(main('https://10.0.2.2:5181/'), NavigationTarget.external);
    });

    test('앱 밖 하위 프레임은 막기만 한다', () {
      expect(classifyNavigation('https://example.com', app, isMainFrame: false), NavigationTarget.blocked);
      expect(classifyNavigation('http://10.0.2.2:5181/x', app, isMainFrame: false), NavigationTarget.app);
    });
  });

  group('bridge', () {
    test('type이 없거나 JSON이 아니면 무시한다', () {
      expect(parseMessage('not json'), isNull);
      expect(parseMessage('[1]'), isNull);
      expect(parseMessage('{"protocol":1}'), isNull);
      expect(parseMessage('{"protocol":1,"type":"ready","path":"/"}')?['type'], 'ready');
    });

    test('init은 계약의 필드를 모두 담는다', () {
      final msg = initMessage(
        platform: 'android',
        appVersion: '1.0.0',
        locale: 'vi-VN',
        padding: const EdgeInsets.fromLTRB(0, 24, 0, 48),
      );
      expect(msg, {
        'protocol': 1,
        'type': 'init',
        'platform': 'android',
        'appVersion': '1.0.0',
        'locale': 'vi-VN',
        'insets': {'top': 24.0, 'right': 0.0, 'bottom': 48.0, 'left': 0.0},
      });
      expect(
        receiveScript(insetsMessage(EdgeInsets.zero)),
        startsWith('window.fornav?.receive({"protocol":1,"type":"insets"'),
      );
    });

    test('onBack 결과는 플랫폼별 참 값을 모두 받는다', () {
      expect(isTrueResult(true), isTrue);
      expect(isTrueResult('true'), isTrue);
      expect(isTrueResult(1), isTrue);
      expect(isTrueResult(false), isFalse);
      expect(isTrueResult('false'), isFalse);
      expect(isTrueResult(null), isFalse);
    });
  });
}
