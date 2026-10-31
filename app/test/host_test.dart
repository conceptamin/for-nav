import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_sign_in/google_sign_in.dart';
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
    group('googleSignIn', () {
    test('features가 비면 init에 넣지 않고, 있으면 그대로 담는다', () {
      Map<String, Object> init(List<String> features) =>
          initMessage(platform: 'ios', appVersion: '1.0.0', locale: 'en-US', padding: EdgeInsets.zero, features: features);
      expect(init(const []).containsKey('features'), isFalse);
      expect(init(const [featureGoogleSignIn])['features'], ['googleSignIn']);
    });

    test('googleSignInResult는 성공이면 idToken, 실패면 error 하나만 담는다', () {
      expect(googleSignInSuccess('eyJ.test.sig'), {'protocol': 1, 'type': 'googleSignInResult', 'idToken': 'eyJ.test.sig'});
      expect(googleSignInFailure(canceled: true), {'protocol': 1, 'type': 'googleSignInResult', 'error': 'canceled'});
      expect(googleSignInFailure(canceled: false), {'protocol': 1, 'type': 'googleSignInResult', 'error': 'failed'});
    });

    test('사용자가 닫은 것만 canceled다', () {
      expect(isSignInCanceled(const GoogleSignInException(code: GoogleSignInExceptionCode.canceled)), isTrue);
      expect(isSignInCanceled(const GoogleSignInException(code: GoogleSignInExceptionCode.interrupted)), isFalse);
      expect(isSignInCanceled(const GoogleSignInException(code: GoogleSignInExceptionCode.clientConfigurationError)), isFalse);
      expect(isSignInCanceled(Exception('network')), isFalse);
    });

    test('Android는 웹 클라이언트 ID만, iOS는 iOS 클라이언트 ID도 있어야 켠다', () {
      expect(nativeSignInConfigured(isIOS: false, webClientId: 'w', iosClientId: ''), isTrue);
      expect(nativeSignInConfigured(isIOS: true, webClientId: 'w', iosClientId: ''), isFalse);
      expect(nativeSignInConfigured(isIOS: true, webClientId: 'w', iosClientId: 'i'), isTrue);
      expect(nativeSignInConfigured(isIOS: false, webClientId: '', iosClientId: 'i'), isFalse);
    });
  });
});

  group('통화 매체(backlog 04)', () {
    test('speechStart의 lang이 없거나 비면 무시한다', () {
      expect(speechLangOf({'type': 'speechStart', 'lang': 'vi-VN'}), 'vi-VN');
      expect(speechLangOf({'type': 'speechStart', 'lang': '  '}), isNull);
      expect(speechLangOf({'type': 'speechStart'}), isNull);
    });

    test('speech·speechError 형식', () {
      expect(speechMessage('xin chào', isFinal: true), {'protocol': 1, 'type': 'speech', 'text': 'xin chào', 'final': true});
      expect(speechErrorMessage(SpeechErrorKind.denied), {'protocol': 1, 'type': 'speechError', 'error': 'denied'});
    });

    test('권한·언어 오류는 바로 끄고, 말 없음은 세지 않고, 그 밖은 이어지면 끈다', () {
      expect(speechErrorKind('error_permission', errorsInRow: 1), SpeechErrorKind.denied);
      expect(speechErrorKind('error_language_not_supported', errorsInRow: 1), SpeechErrorKind.unsupported);
      expect(speechErrorKind('error_no_match', errorsInRow: 99), isNull);
      expect(speechErrorKind('error_network', errorsInRow: 1), isNull);
      expect(speechErrorKind('error_network', errorsInRow: speechMaxErrorsInRow), SpeechErrorKind.unsupported);
      expect(speechErrorCounts('error_no_match'), isFalse);
      expect(speechErrorCounts('error_client'), isTrue);
    });

    test('WebView 권한 요청은 마이크만 허용한다', () {
      expect(isMicrophoneOnlyRequest({'microphone'}), isTrue);
      expect(isMicrophoneOnlyRequest({'microphone', 'camera'}), isFalse);
      expect(isMicrophoneOnlyRequest({}), isFalse);
    });

    test('파일 선택기는 사진을 받는 input에서만 연다', () {
      expect(acceptsImages(['image/*']), isTrue);
      expect(acceptsImages(['']), isTrue);
      expect(acceptsImages(['image/png,image/jpeg']), isTrue);
      expect(acceptsImages(['application/pdf']), isFalse);
    });
  });
}
