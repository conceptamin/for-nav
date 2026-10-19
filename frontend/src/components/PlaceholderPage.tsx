import styles from './PlaceholderPage.module.css';

type PlaceholderPageProps = {
  title: string;
  description: string;
};

// 화면 골격만 제공한다. URL 파라미터나 서버 데이터를 읽거나 표시하지 않는다.
export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <section className={styles.page} aria-labelledby="page-title">
      <title>{`${title} · YardPilot`}</title>
      <h1 id="page-title">{title}</h1>
      <p className={styles.description}>{description}</p>
    </section>
  );
}
