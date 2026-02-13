import { createRoute } from '@granite-js/react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Txt, Top } from '@toss/tds-react-native';

export const Route = createRoute('/about', {
  component: Page,
});

function Page() {
  const navigation = Route.useNavigation();

  return (
    <View style={styles.container}>
      <Top
        title={<Txt typography="t3" fontWeight="bold">이용 안내</Txt>}
        subtitle1={
          <Txt typography="t6" color="#6B7280">
            PDF 파일을 바로 선택하는 기능은 환경 제약에 따라 방식 확정이 필요합니다.
          </Txt>
        }
      />

      <View style={styles.content}>
        <Txt typography="t6" color="#374151">
          현재 우선순위:
        </Txt>
        <Txt typography="t6" color="#6B7280">
          1) 광고 기반 무료 운영(초기){'\n'}
          2) 바른(Bareun) API 기반 검사 유지{'\n'}
          3) 개인 정보(이메일 등) 기본 비수집
        </Txt>

        <Button display="full" onPress={() => navigation.goBack()} viewStyle={styles.button}>
          돌아가기
        </Button>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 24,
    backgroundColor: 'white',
  },
  button: {
    marginTop: 18,
  },
  content: {
    marginTop: 28,
    gap: 10,
  },
});
