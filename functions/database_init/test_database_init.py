
import nuclio_sdk


class TestCase(nuclio_sdk.TestCase):

    def test_check_database(self):
        db_cursor = self._platform.context.user_data.conn.cursor()
        db_cursor.execute(f'insert into test_cases (running_node, logs, result, job, artifact_test) values '
                          f'(1, \'test_logs_text\', \'test_result_text\', 123, \'test_artifact_test text\')')
        db_cursor.execute(f'insert into nodes (current_test_case) values (1)')
        db_cursor.execute(f'insert into jobs (state, artifact_urls, github_username,'
                          f' github_url, commit_sha) values (\'test_state\', \'test_artifact_urls\', '
                          f'\'test_github_username\', \'github_url\', \'commit_sha\')')
        db_cursor.execute(f'insert into users (github_username, slack_username)  values '
                          f'(\'test_github_username\', \'test_slack_username\') ')
