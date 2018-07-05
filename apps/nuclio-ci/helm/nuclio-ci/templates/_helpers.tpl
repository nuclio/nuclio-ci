
{{- define "nuclio-ci.Name" -}}
{{- "nuclioci" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.buildPushArtifacts" -}}
{{- "build_push_artifacts" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.completeTest" -}}
{{- "complete_test" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.databaseInit" -}}
{{- "database-init" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.gatekeeper" -}}
{{- "gatekeeper" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.githubStatusUpdater" -}}
{{- "github_status_updater" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.releaseNode" -}}
{{- "release-node" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.runJob" -}}
{{- "run-job" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.runTestCase" -}}
{{- "run-test-case" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.slackNotifier" -}}
{{- "slack-notifier" | trunc 63 -}}
{{- end -}}
