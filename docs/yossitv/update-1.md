• 診断と fix 生成はありますが、「本当に demo-app
  のファイルを書き換える」まで入っているかは
  fixer 実装次第なので、そこだけ最後に見ます。

• Explored
  └ Read fix_artifact_service.py, fixer.py

────────────────────────────────────────────────

• 半分できていて、半分はまだです。

  できている部分:

  - incident を stored -> diagnosing -> fixing
    -> gating に進める agent 処理はあります。実
    体は agent/orchestrator.py と server/
    services/demo_flow_service.py です。
  - POST /api/agent/run-once を叩けば、diagnosis
    と fix 生成までは走ります。API は server/
    api/agent.py です。

  まだ本物でない部分:

  - agent が demo-app/main.py を実際に書き換える
    end-to-end は、今の既定状態では入っていませ
    ん。
  - fix は主に spec_markdown と diff_preview を
    作る実装で、agent/fixer.py を見ると、Kiro が
    使えないと fallback の擬似 diff を返します。
  - deploy も、TrueFoundry の API key が無いと
    incident は resolved まで進んでも demo-app
    のコード自体は変わりません。

  なので正確には:

  - 「agent が診断して修正案を作る」はできている
  - 「agent がローカルの demo-app を実際に修正し
    て再デプロイする」は、いまはデモ用のモック寄
    り