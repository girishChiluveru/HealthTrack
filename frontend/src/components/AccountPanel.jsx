export default function AccountPanel({ user }) {
  return (
    <section className="card narrow-panel" aria-labelledby="account-heading">
      <h2 id="account-heading">Your account</h2>
      <p className="alert alert--success" role="status">
        You are logged in as a {user.role}.
      </p>
      <dl className="account-details">
        <dt>Name</dt>
        <dd>{user.name}</dd>
        <dt>Email</dt>
        <dd>{user.email}</dd>
        <dt>Timezone</dt>
        <dd>{user.timezone}</dd>
      </dl>
    </section>
  );
}
